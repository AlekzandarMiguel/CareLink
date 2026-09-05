import os
from rest_framework import views, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from apps.referrals.models import Referral, ReferralStatusHistory
from apps.hospitals.models import Hospital, MedicalService, Facility
from .models import CoordinatorOverride
from .matcher import XGBHospitalMatcher
from .clinical_nlp import extract_clinical_syndrome
from .mews import calculate_mews
from .retrainer import train_and_export_model, FEATURE_NAMES

class ReferralMatchingRecommendationsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            referral = Referral.objects.select_related(
                'requesting_hospital', 'required_service', 'required_facility', 'patient'
            ).get(pk=pk)
        except Referral.DoesNotExist:
            return Response({'detail': 'Referral not found.'}, status=status.HTTP_404_NOT_FOUND)

        notes = f"{referral.patient.clinical_summary} {referral.reason_for_referral or ''} {referral.additional_requirements or ''}"
        syndrome_data = extract_clinical_syndrome(notes)

        recommendations = XGBHospitalMatcher.rank_hospitals_for_referral(referral)
        return Response({
            'referral_id': referral.id,
            'referral_code': referral.referral_code,
            'requesting_hospital': referral.requesting_hospital.hospital_name,
            'required_service': referral.required_service.name if referral.required_service else None,
            'urgency': referral.urgency,
            'syndrome': syndrome_data,
            'total_candidates': len(recommendations),
            'recommendations': recommendations
        })

class DraftReferralPreviewRecommendationsView(views.APIView):
    """
    Real-time AI Recommendation endpoint for Referring Staff during referral creation.
    Allows doctors to input clinical parameters and vitals to receive live top-hospital matches and MEWS score.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        user = request.user

        # Identify requesting hospital
        req_hosp_id = data.get('requesting_hospital_id')
        if req_hosp_id:
            try:
                req_hosp = Hospital.objects.get(pk=req_hosp_id)
            except Hospital.DoesNotExist:
                req_hosp = getattr(user, 'hospital', None)
        else:
            req_hosp = getattr(user, 'hospital', None)

        if not req_hosp:
            req_hosp = Hospital.objects.filter(verification_status=Hospital.VerificationStatus.APPROVED).first()

        if not req_hosp:
            return Response({'detail': 'Requesting hospital context required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Service & Facility
        service_id = data.get('required_service_id') or data.get('service_id')
        facility_id = data.get('required_facility_id') or data.get('facility_id')
        urgency = data.get('urgency', 'ROUTINE')

        req_service = None
        if service_id:
            req_service = MedicalService.objects.filter(pk=service_id).first()

        req_facility = None
        if facility_id:
            req_facility = Facility.objects.filter(pk=facility_id).first()

        # Clinical notes / chief complaint
        clinical_notes = (data.get('clinical_summary') or '') + ' ' + (data.get('reason_for_referral') or '')
        syndrome_data = extract_clinical_syndrome(clinical_notes)

        # Vitals & MEWS
        mews_data = calculate_mews(
            systolic_bp=data.get('systolic_bp'),
            heart_rate=data.get('heart_rate'),
            resp_rate=data.get('resp_rate'),
            temperature=data.get('temperature'),
            avpu=data.get('avpu', 'A'),
            spo2=data.get('spo2')
        )

        recommendations = XGBHospitalMatcher.rank_candidates(
            req_hosp=req_hosp,
            required_service=req_service,
            required_facility=req_facility,
            urgency=urgency,
            mews_data=mews_data,
            syndrome_data=syndrome_data,
            max_results=int(data.get('max_results', 5))
        )

        return Response({
            'requesting_hospital': req_hosp.hospital_name,
            'mews': mews_data,
            'syndrome': syndrome_data,
            'recommendations': recommendations
        })

class CoordinatorOverrideView(views.APIView):
    """
    Submits a coordinator override when routing a patient to a facility different from
    the #1 AI recommendation, recording clinical justifications and applying temporary dynamic penalties.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            referral = Referral.objects.get(pk=pk)
        except Referral.DoesNotExist:
            return Response({'detail': 'Referral not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        rec_hosp_id = data.get('recommended_hospital_id')
        sel_hosp_id = data.get('selected_hospital_id')
        reason_code = data.get('reason_code', CoordinatorOverride.ReasonCode.PHYSICIAN_DISCRETION)
        notes = data.get('justification_notes', '')

        try:
            rec_hosp = Hospital.objects.get(pk=rec_hosp_id)
            sel_hosp = Hospital.objects.get(pk=sel_hosp_id)
        except Hospital.DoesNotExist:
            return Response({'detail': 'Recommended or selected hospital not found.'}, status=status.HTTP_400_BAD_REQUEST)

        override = CoordinatorOverride.objects.create(
            referral=referral,
            recommended_hospital=rec_hosp,
            selected_hospital=sel_hosp,
            reason_code=reason_code,
            justification_notes=notes,
            coordinator=request.user
        )

        # Dynamic temporary penalty propagation on recommended hospital if operational obstacle reported
        if reason_code in ['CT_SCAN_OFFLINE', 'SURGEON_UNAVAILABLE', 'EMERGENCY_BAY_SATURATED', 'EQUIPMENT_MAINTENANCE']:
            penalties = rec_hosp.temporary_penalties or {}
            penalties[reason_code] = {
                'reported_at': timezone.now().isoformat(),
                'penalty_points': 15,
                'notes': notes
            }
            rec_hosp.temporary_penalties = penalties
            rec_hosp.save(update_fields=['temporary_penalties'])

        # Transition the referral to selected hospital
        old_status = referral.status
        referral.receiving_hospital = sel_hosp
        referral.status = Referral.Status.UNDER_REVIEW
        referral.save(update_fields=['receiving_hospital', 'status', 'updated_at'])

        ReferralStatusHistory.objects.create(
            referral=referral,
            from_status=old_status,
            to_status=Referral.Status.UNDER_REVIEW,
            changed_by=request.user,
            notes=f"Coordinator Override: Routed to {sel_hosp.hospital_name} instead of recommended {rec_hosp.hospital_name}. Reason: {reason_code}. Justification: {notes}"
        )

        return Response({
            'detail': f'Override recorded. Referral successfully routed to {sel_hosp.hospital_name}.',
            'override_id': override.id,
            'reason_code': override.reason_code,
            'selected_hospital': sel_hosp.hospital_name
        }, status=status.HTTP_201_CREATED)

class CoordinatorOverrideListView(views.APIView):
    """
    Returns history of coordinator overrides for audit and model calibration.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        overrides = CoordinatorOverride.objects.select_related(
            'referral', 'recommended_hospital', 'selected_hospital', 'coordinator'
        ).all()[:50]

        data = [{
            'id': o.id,
            'referral_code': o.referral.referral_code,
            'recommended_hospital': o.recommended_hospital.hospital_name,
            'selected_hospital': o.selected_hospital.hospital_name,
            'reason_code': o.reason_code,
            'reason_display': o.get_reason_code_display(),
            'notes': o.justification_notes,
            'coordinator_email': o.coordinator.email if o.coordinator else 'System',
            'created_at': o.created_at.isoformat()
        } for o in overrides]

        return Response({'count': len(data), 'results': data})

class ModelRetrainView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'ADMIN' and not request.user.is_staff:
            return Response({'detail': 'Administrator privileges required to retrain AI model.'}, 
                            status=status.HTTP_403_FORBIDDEN)

        try:
            metrics = train_and_export_model()
            XGBHospitalMatcher.get_model(force_reload=True)
            return Response({
                'detail': 'XGBoost Hospital Matching Model retrained and deployed successfully.',
                'metrics': metrics
            })
        except Exception as e:
            return Response({
                'detail': f'Model retraining failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ModelStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        model = XGBHospitalMatcher.get_model()
        n_features = getattr(model, 'n_features_in_', 0) if model else 0
        return Response({
            'model_type': 'XGBoost Multi-Objective Hospital Matching Engine',
            'is_loaded': model is not None,
            'n_features': n_features,
            'features': FEATURE_NAMES,
            'capabilities': [
                'Clinical MEWS Vital Severity Scoring',
                'Clinical NLP Emergency Syndrome & Golden Hour Recognition',
                'Real-World Road Routing & Corridor Speeds (Sayre Hwy & Metro corridors)',
                'Condition-Specific Time Windows (STEMI 90m Door-to-Balloon, Stroke 4.5h, Trauma 60m)',
                'Active On-Call Specialist Shift Availability Check',
                'Multi-Objective Pareto Optimization (Acceptance, Intake Velocity, Clinical Experience)',
                'Explainable AI Waterfall Feature Contributions',
                'Continuous Feedback Loop with Coordinator Overrides'
            ]
        })
