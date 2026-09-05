"""
Modified Early Warning Score (MEWS) & Clinical Severity Scoring Engine.
Provides standardized bedside risk assessment:
- Systolic Blood Pressure (mmHg)
- Heart Rate (bpm)
- Respiratory Rate (breaths/min)
- Body Temperature (deg C)
- Neurological AVPU (Alert, Voice, Pain, Unresponsive)
- Oxygen Saturation / SpO2 (%)
"""

def calculate_mews(systolic_bp=None, heart_rate=None, resp_rate=None, 
                   temperature=None, avpu='A', spo2=None):
    score = 0
    factors = []
    
    # 1. Systolic Blood Pressure
    if systolic_bp is not None:
        try:
            sbp = float(systolic_bp)
            if sbp <= 70:
                score += 3
                factors.append(f"Severe hypotension (SBP {int(sbp)} mmHg)")
            elif 71 <= sbp <= 80:
                score += 2
                factors.append(f"Moderate hypotension (SBP {int(sbp)} mmHg)")
            elif 81 <= sbp <= 100:
                score += 1
                factors.append(f"Mild hypotension (SBP {int(sbp)} mmHg)")
            elif 101 <= sbp <= 199:
                score += 0
            else: # >= 200
                score += 2
                factors.append(f"Severe hypertension (SBP {int(sbp)} mmHg)")
        except (ValueError, TypeError):
            pass

    # 2. Heart Rate
    if heart_rate is not None:
        try:
            hr = float(heart_rate)
            if hr <= 40:
                score += 2
                factors.append(f"Severe bradycardia (HR {int(hr)} bpm)")
            elif 41 <= hr <= 50:
                score += 1
                factors.append(f"Mild bradycardia (HR {int(hr)} bpm)")
            elif 51 <= hr <= 100:
                score += 0
            elif 101 <= hr <= 110:
                score += 1
                factors.append(f"Mild tachycardia (HR {int(hr)} bpm)")
            elif 111 <= hr <= 129:
                score += 2
                factors.append(f"Moderate tachycardia (HR {int(hr)} bpm)")
            else: # >= 130
                score += 3
                factors.append(f"Severe tachycardia (HR {int(hr)} bpm)")
        except (ValueError, TypeError):
            pass

    # 3. Respiratory Rate
    if resp_rate is not None:
        try:
            rr = float(resp_rate)
            if rr < 9:
                score += 2
                factors.append(f"Bradypnea (RR {int(rr)}/min)")
            elif 9 <= rr <= 14:
                score += 0
            elif 15 <= rr <= 20:
                score += 1
            elif 21 <= rr <= 29:
                score += 2
                factors.append(f"Tachypnea (RR {int(rr)}/min)")
            else: # >= 30
                score += 3
                factors.append(f"Severe tachypnea (RR {int(rr)}/min)")
        except (ValueError, TypeError):
            pass

    # 4. Temperature (deg C)
    if temperature is not None:
        try:
            temp = float(temperature)
            if temp < 35.0:
                score += 2
                factors.append(f"Hypothermia ({temp:.1f}C)")
            elif 35.0 <= temp <= 38.4:
                score += 0
            else: # >= 38.5
                score += 2
                factors.append(f"High fever ({temp:.1f}C)")
        except (ValueError, TypeError):
            pass

    # 5. Neurological AVPU
    avpu_str = str(avpu).upper().strip() if avpu else 'A'
    if avpu_str == 'A':
        score += 0
    elif avpu_str == 'V':
        score += 1
        factors.append("Altered mental status: Reacting only to Voice (V)")
    elif avpu_str == 'P':
        score += 2
        factors.append("Severe neurological impairment: Reacting only to Pain (P)")
    elif avpu_str == 'U':
        score += 3
        factors.append("Unresponsive / Comatose (U)")

    # 6. Supplementary: SpO2 Hypoxia assessment
    if spo2 is not None:
        try:
            sat = float(spo2)
            if sat < 90:
                score += 2
                factors.append(f"Critical desaturation (SpO2 {int(sat)}%)")
            elif 90 <= sat <= 94:
                score += 1
                factors.append(f"Mild hypoxia (SpO2 {int(sat)}%)")
        except (ValueError, TypeError):
            pass

    # Stratify risk level & recommended care
    if score >= 6:
        risk_level = 'CRITICAL'
        recommended_care = 'INTENSIVE_CARE_UNIT'
        badge_color = 'rose'
    elif score >= 4:
        risk_level = 'HIGH'
        recommended_care = 'HIGH_DEPENDENCY_OR_ICU'
        badge_color = 'amber'
    elif score >= 2:
        risk_level = 'MODERATE'
        recommended_care = 'MONITORED_STEP_DOWN'
        badge_color = 'sky'
    else:
        risk_level = 'LOW'
        recommended_care = 'STANDARD_WARD'
        badge_color = 'emerald'

    return {
        'mews_score': score,
        'risk_level': risk_level,
        'recommended_care': recommended_care,
        'badge_color': badge_color,
        'clinical_alerts': factors,
        'is_unstable': score >= 4
    }
