import math
import os
import re
import datetime
import joblib
import numpy as np
from django.conf import settings
from apps.hospitals.models import Hospital
from apps.transfers.models import Transfer
from .mews import calculate_mews
from .clinical_nlp import extract_clinical_syndrome
from .routing import calculate_corridor_routing, haversine_distance

def extract_vitals_from_text(clinical_text):
    """
    Robust clinical regex parser to extract vitals from clinical summaries/notes if entered in free-text:
    e.g. 'BP: 90/60, HR: 118, RR: 24, Temp: 38.6C, SpO2: 92%'
    """
    if not clinical_text:
        return {}
    
    text = str(clinical_text).lower()
    vitals = {}
    
    # Blood pressure: BP 120/80, SBP 90
    bp_match = re.search(r'(?:bp|sbp|blood pressure)[:\s]+(\d{2,3})(?:/\d{2,3})?', text)
    if bp_match:
        try:
            vitals['systolic_bp'] = float(bp_match.group(1))
        except (ValueError, TypeError):
            pass
            
    # Heart rate: HR 110, pulse 95
    hr_match = re.search(r'(?:hr|pulse|heart rate)[:\s]+(\d{2,3})', text)
    if hr_match:
        try:
            vitals['heart_rate'] = float(hr_match.group(1))
        except (ValueError, TypeError):
            pass

    # Respiratory rate: RR 22, resp 18
    rr_match = re.search(r'(?:rr|resp|respiratory rate)[:\s]+(\d{1,2})', text)
    if rr_match:
        try:
            vitals['resp_rate'] = float(rr_match.group(1))
        except (ValueError, TypeError):
            pass

    # Temperature: temp 38.5, 37C
    temp_match = re.search(r'(?:temp|temperature)[:\s]+(\d{2}(?:\.\d)?)', text)
    if temp_match:
        try:
            vitals['temperature'] = float(temp_match.group(1))
        except (ValueError, TypeError):
            pass

    # SpO2: spo2 94%, o2 sat 91%
    spo2_match = re.search(r'(?:spo2|sat|o2)[:\s]+(\d{2,3})%?', text)
    if spo2_match:
        try:
            vitals['spo2'] = float(spo2_match.group(1))
        except (ValueError, TypeError):
            pass

    return vitals


class XGBHospitalMatcher:
    _model = None

    @classmethod
    def get_model(cls, force_reload=False):
        if cls._model is None or force_reload:
            model_path = getattr(settings, 'ML_MODEL_PATH', None)
            if model_path and os.path.exists(model_path):
                try:
                    cls._model = joblib.load(model_path)
                except Exception as e:
                    print(f"Notice: Could not load XGBoost model from {model_path}: {e}")
                    cls._model = None
        return cls._model

    @classmethod
    def rank_hospitals_for_referral(cls, referral, max_results=10, vitals_override=None):
        req_hosp = referral.requesting_hospital
        required_service = referral.required_service
        required_facility = referral.required_facility
        urgency = referral.urgency

        # Clinical free-text combination
        notes = f"{referral.patient.clinical_summary} {referral.reason_for_referral or ''} {referral.additional_requirements or ''}"

        # 1. Clinical NLP Extraction: Identify emergency syndrome & golden hour window
        syndrome_data = extract_clinical_syndrome(notes)
        if syndrome_data.get('detected') and syndrome_data.get('urgency_override') == 'EMERGENCY':
            urgency = 'EMERGENCY'

        # 2. Extract vitals from clinical text if not explicitly provided
        vitals = vitals_override or {}
        if not vitals:
            vitals = extract_vitals_from_text(notes)

        # 3. Compute MEWS severity
        mews_data = calculate_mews(
            systolic_bp=vitals.get('systolic_bp'),
            heart_rate=vitals.get('heart_rate'),
            resp_rate=vitals.get('resp_rate'),
            temperature=vitals.get('temperature'),
            avpu=vitals.get('avpu', 'A'),
            spo2=vitals.get('spo2')
        )

        return cls.rank_candidates(
            req_hosp=req_hosp,
            required_service=required_service,
            required_facility=required_facility,
            urgency=urgency,
            mews_data=mews_data,
            syndrome_data=syndrome_data,
            max_results=max_results
        )

    @classmethod
    def rank_candidates(cls, req_hosp, required_service, required_facility, urgency,
                        mews_data=None, syndrome_data=None, max_results=10):
        if mews_data is None:
            mews_data = calculate_mews()
        if syndrome_data is None:
            syndrome_data = extract_clinical_syndrome('')

        # Candidate pool: Approved, Operational, Exclude requesting hospital
        candidates = Hospital.objects.filter(
            verification_status=Hospital.VerificationStatus.APPROVED
        ).exclude(id=req_hosp.id).prefetch_related('services', 'facilities', 'specialties')

        # Calculate active inbound in-transit transfers per hospital
        active_inbound = {}
        inbound_transfers = Transfer.objects.filter(
            status__in=['DISPATCHED', 'PICKED_UP', 'IN_TRANSIT', 'ARRIVED']
        ).values_list('referral__receiving_hospital_id', flat=True)

        for hid in inbound_transfers:
            if hid:
                active_inbound[hid] = active_inbound.get(hid, 0) + 1

        results = []
        model = cls.get_model()
        n_features = getattr(model, 'n_features_in_', 10) if model else 0

        time_window_max = syndrome_data.get('time_window_mins') or 180
        target_window = syndrome_data.get('target_window_mins') or 120
        required_specialist = syndrome_data.get('required_specialist')

        for cand in candidates:
            # Service & Facility Matching
            service_match = 1.0 if (required_service and required_service in cand.services.all()) else 0.0
            facility_match = 1.0 if (not required_facility or required_facility in cand.facilities.all()) else 0.0

            # Real-World Road Routing with Corridor Speeds & Peak Traffic
            route_info = calculate_corridor_routing(
                req_hosp.latitude, req_hosp.longitude,
                cand.latitude, cand.longitude
            )
            straight_dist = route_info['straight_distance_km']
            road_dist = route_info['road_distance_km']
            eta_mins = route_info['travel_time_mins']
            corridor_type = route_info['corridor_type']

            urgency_factor = 3.0 if urgency == 'EMERGENCY' else (2.0 if urgency == 'URGENT' else 1.0)
            inbound_congestion = active_inbound.get(cand.id, 0)

            # Effective Capacity (deducting inbound ambulances)
            effective_beds = max(0, cand.available_beds - inbound_congestion)
            effective_icu = max(0, cand.available_icu_beds - (1 if inbound_congestion > 0 else 0))

            bed_availability_ratio = effective_beds / max(cand.bed_capacity, 1)
            icu_availability_ratio = effective_icu / max(cand.icu_capacity, 1)

            # Historical acceptance rate calculation
            past_referrals = cand.incoming_referrals.exclude(status='DRAFT')
            total_past = past_referrals.count()
            accepted_past = past_referrals.filter(status__in=[
                'ACCEPTED', 'TRANSFER_PENDING', 'TRANSFER_ASSIGNED', 
                'DISPATCHED', 'PICKED_UP', 'IN_TRANSIT', 'ARRIVED', 
                'HANDED_OVER', 'COMPLETED'
            ]).count()
            historical_acceptance = (accepted_past / total_past) if total_past > 0 else 0.85

            mews_score = mews_data.get('mews_score', 0)

            # On-Call Specialist Status
            specialist_on_duty = False
            specialist_name = None
            if required_specialist and cand.on_call_specialists:
                specialist_on_duty = bool(cand.on_call_specialists.get(required_specialist, False))
                specialist_name = required_specialist.replace('_', ' ').title()
            elif required_specialist:
                specialist_on_duty = False
                specialist_name = required_specialist.replace('_', ' ').title()
            else:
                # Default general duty
                specialist_on_duty = bool(cand.on_call_specialists.get('emergency_medicine', True))
                specialist_name = 'Emergency Medicine'

            # Time Window & Golden Hour Feasibility
            window_compliance_ratio = min(2.0, eta_mins / max(1, time_window_max))
            is_window_exceeded = eta_mins > time_window_max
            is_window_optimal = eta_mins <= target_window

            # Feature Contributions for Explainable AI (SHAP-like waterfall)
            contributions = []

            # 1. Service & Facility Contribution
            if service_match:
                contributions.append({
                    'category': 'Clinical Capability',
                    'name': 'Service Match',
                    'impact_pct': 28,
                    'direction': 'positive',
                    'detail': f"Provides required specialty service ({required_service.name if required_service else 'General Service'})"
                })
            else:
                contributions.append({
                    'category': 'Clinical Capability',
                    'name': 'Service Mismatch',
                    'impact_pct': -45,
                    'direction': 'negative',
                    'detail': f"Does not list {required_service.name if required_service else 'service'} as standard capability"
                })

            if facility_match and required_facility:
                contributions.append({
                    'category': 'Facility Alignment',
                    'name': 'Critical Facility Available',
                    'impact_pct': 14,
                    'direction': 'positive',
                    'detail': f"Equipped with {required_facility.name}"
                })
            elif required_facility and not facility_match:
                contributions.append({
                    'category': 'Facility Alignment',
                    'name': 'Facility Deficit',
                    'impact_pct': -18,
                    'direction': 'negative',
                    'detail': f"Lacks {required_facility.name}"
                })

            # 2. Road Transit & Traffic Corridor Contribution
            if eta_mins <= 15:
                contributions.append({
                    'category': 'Transit & Logistics',
                    'name': 'Immediate Corridor Proximity',
                    'impact_pct': 18,
                    'direction': 'positive',
                    'detail': f"Rapid transit ~{eta_mins} mins ({road_dist} km via {corridor_type})"
                })
            elif eta_mins <= 35:
                contributions.append({
                    'category': 'Transit & Logistics',
                    'name': 'Manageable Driving Corridor',
                    'impact_pct': 8,
                    'direction': 'positive',
                    'detail': f"Estimated transit ~{eta_mins} mins ({road_dist} km)"
                })
            elif eta_mins <= 60:
                contributions.append({
                    'category': 'Transit & Logistics',
                    'name': 'Moderate Transit Distance',
                    'impact_pct': -5,
                    'direction': 'negative',
                    'detail': f"Transit ~{eta_mins} mins ({road_dist} km driving corridor)"
                })
            else:
                contributions.append({
                    'category': 'Transit & Logistics',
                    'name': 'Extended Transit Distance',
                    'impact_pct': -16,
                    'direction': 'negative',
                    'detail': f"Lengthy travel time ~{eta_mins} mins ({road_dist} km driving corridor)"
                })

            # 3. Golden Hour & Door-to-Balloon Window Compliance
            if syndrome_data.get('detected'):
                window_name = syndrome_data.get('window_name', 'Clinical Window')
                if is_window_optimal:
                    contributions.append({
                        'category': 'Time-Critical Window',
                        'name': f"{window_name} (Optimal)",
                        'impact_pct': 16,
                        'direction': 'positive',
                        'detail': f"ETA {eta_mins}m is well within optimal window ({target_window}m)"
                    })
                elif not is_window_exceeded:
                    contributions.append({
                        'category': 'Time-Critical Window',
                        'name': f"{window_name} (Acceptable)",
                        'impact_pct': 5,
                        'direction': 'positive',
                        'detail': f"ETA {eta_mins}m is within maximum threshold ({time_window_max}m)"
                    })
                else:
                    over_mins = eta_mins - time_window_max
                    contributions.append({
                        'category': 'Time-Critical Window',
                        'name': f"{window_name} Exceeded",
                        'impact_pct': -30,
                        'direction': 'negative',
                        'detail': f"ETA {eta_mins}m exceeds critical viability cutoff of {time_window_max}m (+{over_mins}m delay)"
                    })

            # 4. Specialist On-Call Status Contribution
            if required_specialist:
                if specialist_on_duty:
                    contributions.append({
                        'category': 'Specialist Roster',
                        'name': 'Specialist On-Duty',
                        'impact_pct': 12,
                        'direction': 'positive',
                        'detail': f"{specialist_name} confirmed on active on-call duty"
                    })
                else:
                    contributions.append({
                        'category': 'Specialist Roster',
                        'name': 'Specialist Not On Duty',
                        'impact_pct': -15,
                        'direction': 'negative',
                        'detail': f"{specialist_name} is on standby call-in only"
                    })

            # 5. Capacity & Inbound Congestion Contribution
            if inbound_congestion > 0:
                contributions.append({
                    'category': 'Hospital Congestion',
                    'name': 'Inbound Ambulance Load',
                    'impact_pct': -min(18, inbound_congestion * 6),
                    'direction': 'negative',
                    'detail': f"{inbound_congestion} inbound emergency transfer(s) en route to bay"
                })

            if effective_beds > 5:
                contributions.append({
                    'category': 'Bed Availability',
                    'name': 'General Bed Reserve',
                    'impact_pct': 7,
                    'direction': 'positive',
                    'detail': f"{effective_beds} inpatient beds unoccupied"
                })
            elif effective_beds == 0:
                contributions.append({
                    'category': 'Bed Availability',
                    'name': 'Bed Saturation Warning',
                    'impact_pct': -14,
                    'direction': 'negative',
                    'detail': "0 net inpatient beds remaining"
                })

            if urgency == 'EMERGENCY' or mews_score >= 4:
                if effective_icu > 0:
                    contributions.append({
                        'category': 'Critical Care Capacity',
                        'name': 'ICU Bed Availability',
                        'impact_pct': 15,
                        'direction': 'positive',
                        'detail': f"{effective_icu} intensive care beds open for admission"
                    })
                else:
                    contributions.append({
                        'category': 'Critical Care Capacity',
                        'name': 'Zero ICU Capacity',
                        'impact_pct': -25,
                        'direction': 'negative',
                        'detail': "0 ICU beds available for high-acuity / MEWS critical patient"
                    })

            if cand.diversion_status:
                contributions.append({
                    'category': 'Hospital Status',
                    'name': 'Emergency Divert',
                    'impact_pct': -35,
                    'direction': 'negative',
                    'detail': "Hospital is currently on official Emergency Department Divert"
                })

            # 2. Match Score Prediction via Model or Multi-Objective Pareto
            model_prob = None
            if model:
                try:
                    if n_features == 12:
                        features = np.array([[
                            service_match,
                            facility_match,
                            road_dist,
                            float(eta_mins),
                            urgency_factor,
                            float(mews_score),
                            bed_availability_ratio,
                            icu_availability_ratio,
                            float(inbound_congestion),
                            historical_acceptance,
                            1.0 if specialist_on_duty else 0.0,
                            1.0 if not is_window_exceeded else 0.0
                        ]])
                    elif n_features == 10:
                        features = np.array([[
                            service_match,
                            facility_match,
                            road_dist,
                            float(eta_mins),
                            urgency_factor,
                            float(mews_score),
                            bed_availability_ratio,
                            icu_availability_ratio,
                            float(inbound_congestion),
                            historical_acceptance
                        ]])
                    else:
                        features = np.array([[
                            service_match,
                            facility_match,
                            min(straight_dist, 150.0),
                            urgency_factor,
                            bed_availability_ratio,
                            icu_availability_ratio,
                            historical_acceptance
                        ]])
                    model_prob = float(model.predict_proba(features)[0][1])
                except Exception as ex:
                    model_prob = None

            # Multi-Objective Pareto Components:
            # 1) Acceptance Probability (0-100)
            acceptance_score = (model_prob * 100.0) if model_prob is not None else (
                85.0 if service_match > 0 else 10.0
            )

            # 2) Intake Velocity Score (0-100): Faster turnaround if less inbound congestion & more free beds
            intake_velocity_score = max(10.0, 100.0 - (inbound_congestion * 16.0) - (0.0 if effective_beds > 5 else 25.0))

            # 3) Clinical Experience & Specialty Tier (0-100)
            h_type = cand.hospital_type
            if h_type == Hospital.HospitalType.SPECIALTY:
                clinical_experience_score = 96.0
            elif h_type == Hospital.HospitalType.APEX_TRAUMA:
                clinical_experience_score = 92.0
            elif h_type == Hospital.HospitalType.TERTIARY:
                clinical_experience_score = 82.0
            else:
                clinical_experience_score = 64.0

            # 4) Time Window Feasibility (0-100)
            if eta_mins <= target_window:
                time_window_score = 100.0
            elif eta_mins <= time_window_max:
                time_window_score = max(50.0, 100.0 - ((eta_mins - target_window) / max(1, time_window_max - target_window)) * 45.0)
            else:
                time_window_score = max(5.0, 45.0 - ((eta_mins - time_window_max) * 0.7))

            # Specialty affinity boosts
            affinity_bonus = 0.0
            if service_match > 0 and required_service:
                s_lower = required_service.name.lower()
                h_lower = cand.hospital_name.lower()
                if ('cardio' in s_lower or 'heart' in s_lower) and ('heart' in h_lower or h_type == Hospital.HospitalType.SPECIALTY):
                    affinity_bonus += 8.0
                elif ('nephro' in s_lower or 'kidney' in s_lower or 'dialysis' in s_lower) and ('kidney' in h_lower or h_type == Hospital.HospitalType.SPECIALTY):
                    affinity_bonus += 8.0
                elif ('pediatric' in s_lower or 'child' in s_lower or 'neonat' in s_lower) and ('child' in h_lower or h_type == Hospital.HospitalType.SPECIALTY):
                    affinity_bonus += 8.0
                elif ('trauma' in s_lower or 'neuro' in s_lower or 'ortho' in s_lower) and h_type == Hospital.HospitalType.APEX_TRAUMA:
                    affinity_bonus += 7.0

            if specialist_on_duty:
                affinity_bonus += 4.0
            elif required_specialist and not specialist_on_duty:
                affinity_bonus -= 10.0

            if cand.diversion_status:
                affinity_bonus -= 30.0

            # Composite Pareto Optimization Score
            if service_match > 0:
                composite_score = (
                    0.35 * acceptance_score +
                    0.25 * time_window_score +
                    0.20 * intake_velocity_score +
                    0.20 * clinical_experience_score +
                    affinity_bonus
                )
                match_score = int(round(max(15, min(99, composite_score))))
            else:
                match_score = 5

            # Clinical Explanation Factors
            factors = []
            if service_match:
                factors.append(f"Provides required service ({required_service.name})")
            else:
                factors.append(f"Does not list {required_service.name if required_service else 'service'} as standard service")

            if required_facility:
                if facility_match:
                    factors.append(f"Has required facility ({required_facility.name})")
                else:
                    factors.append(f"Lacks {required_facility.name}")

            factors.append(f"ETA ~{eta_mins} mins ({road_dist} km driving corridor via {corridor_type})")

            if syndrome_data.get('detected'):
                w_name = syndrome_data.get('window_name')
                if is_window_optimal:
                    factors.append(f"Time Window: Optimal {w_name} ({eta_mins}m <= {target_window}m target)")
                elif not is_window_exceeded:
                    factors.append(f"Time Window: Within safe {w_name} ({eta_mins}m <= {time_window_max}m cutoff)")
                else:
                    factors.append(f"Clinical Alert: Exceeds safe {w_name} by {eta_mins - time_window_max} mins")

            if required_specialist:
                if specialist_on_duty:
                    factors.append(f"Specialist Roster: {specialist_name} on active duty")
                else:
                    factors.append(f"Specialist Roster Alert: {specialist_name} is on call-in standby only")

            if inbound_congestion > 0:
                factors.append(f"Net {effective_beds} beds free ({inbound_congestion} inbound ambulance en route)")
            elif effective_beds > 5:
                factors.append(f"Sufficient bed capacity ({effective_beds} beds free)")

            if (urgency == 'EMERGENCY' or mews_score >= 4):
                if effective_icu > 0:
                    factors.append(f"ICU emergency capacity available ({effective_icu} ICU beds)")
                else:
                    factors.append("Critical Capacity Warning: 0 available ICU beds for emergency patient")

            if mews_data.get('is_unstable'):
                factors.append(f"Clinical MEWS Alert: Score {mews_score} ({mews_data.get('risk_level')}) - requires immediate triage")

            is_eligible = (service_match > 0) and (cand.operating_status == Hospital.OperatingStatus.OPERATIONAL) and not cand.diversion_status

            # Time Window Status
            if is_window_optimal:
                window_status = 'OPTIMAL'
            elif not is_window_exceeded:
                window_status = 'SAFE'
            else:
                window_status = 'EXCEEDED'

            results.append({
                'hospital_id': cand.id,
                'hospital_name': cand.hospital_name,
                'hospital_code': cand.hospital_code,
                'hospital_type': cand.get_hospital_type_display(),
                'city': cand.city,
                'province': cand.province,
                'distance_km': road_dist,
                'straight_distance_km': straight_dist,
                'eta_minutes': eta_mins,
                'corridor_type': corridor_type,
                'match_score': match_score,
                'is_eligible': is_eligible,
                'operating_status': cand.operating_status,
                'diversion_status': cand.diversion_status,
                'available_beds': cand.available_beds,
                'effective_available_beds': effective_beds,
                'available_icu_beds': cand.available_icu_beds,
                'effective_icu_beds': effective_icu,
                'inbound_in_transit': inbound_congestion,
                'specialist_on_duty': specialist_on_duty,
                'specialist_name': specialist_name,
                'window_status': window_status,
                'time_window_mins': time_window_max,
                'target_window_mins': target_window,
                'pareto_breakdown': {
                    'acceptance_prob_pct': int(round(acceptance_score)),
                    'intake_velocity_pct': int(round(intake_velocity_score)),
                    'clinical_experience_pct': int(round(clinical_experience_score)),
                    'time_window_score_pct': int(round(time_window_score))
                },
                'feature_contributions': contributions,
                'explanation_factors': factors,
                'contact_number': cand.contact_number,
                'emergency_contact': cand.emergency_contact or cand.contact_number,
            })

        # Rank: Eligible first, then highest match score, then shortest ETA
        results.sort(key=lambda x: (x['is_eligible'], x['match_score'], -x['eta_minutes']), reverse=True)
        return results[:max_results]
