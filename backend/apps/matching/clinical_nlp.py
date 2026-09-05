"""
Clinical NLP & Diagnostic Pattern Extraction Engine for CareLink
Extracts critical emergency syndromes, acuity markers, and required clinical capabilities
from free-text clinical notes, chief complaints, and physician referral notes.
"""
import re

EMERGENCY_SYNDROMES = {
    'STEMI': {
        'code': 'STEMI',
        'label': 'ST-Elevation Myocardial Infarction (STEMI)',
        'window_name': 'Door-to-Balloon (PCI) Window',
        'max_window_mins': 90,
        'target_window_mins': 60,
        'required_service_keywords': ['cardio', 'heart', 'coronary', 'interventional cardiology'],
        'required_facility_keywords': ['cath lab', 'catheterization', 'cardiac icu', 'coronary care'],
        'required_specialist': 'interventional_cardiology',
        'urgency': 'EMERGENCY',
        'patterns': [
            r'\bstemi\b',
            r'\bst[\s\-]?elevation\b',
            r'inferior[\s\-]+wall[\s\-]+(infarct|mi|stemi)',
            r'anterior[\s\-]+wall[\s\-]+(infarct|mi|stemi)',
            r'anteroseptal[\s\-]+(infarct|mi|stemi)',
            r'acute[\s\-]+coronary[\s\-]+syndrome',
            r'troponin[\s\-]+(positive|elevated|\>\s*0\.\d+|\>\s*\d+)',
            r'crushing[\s\-]+chest[\s\-]+pain.*radiat',
            r'substernal[\s\-]+chest[\s\-]+pain.*diaphoresis',
            r'myocardial[\s\-]+infarction',
            r'ecg.*st[\s\-]?elevation'
        ]
    },
    'STROKE': {
        'code': 'STROKE',
        'label': 'Acute Ischemic Stroke / Cerebrovascular Accident',
        'window_name': 'Thrombolysis / Thrombectomy Window',
        'max_window_mins': 270,   # 4.5 hours for IV rtPA; up to 360m for EVT
        'target_window_mins': 180,
        'required_service_keywords': ['neuro', 'stroke', 'neurology', 'neurosurgery'],
        'required_facility_keywords': ['ct', 'computed tomography', 'mri', 'stroke unit', 'interventional radiology'],
        'required_specialist': 'stroke_neurology',
        'urgency': 'EMERGENCY',
        'patterns': [
            r'\bcva\b',
            r'\bstroke\b',
            r'cerebrovascular[\s\-]+accident',
            r'acute[\s\-]+ischemic[\s\-]+stroke',
            r'intracranial[\s\-]+hemorrhage',
            r'\bich\b',
            r'hemiparesis',
            r'facial[\s\-]+droop',
            r'slurred[\s\-]+speech',
            r'sudden[\s\-]+aphasia',
            r'nihss[\s\-]?[:=]?\s*\d+',
            r'onset[\s\-]+of[\s\-]+weakness',
            r'dense[\s\-]+hemiplegia'
        ]
    },
    'TRAUMA': {
        'code': 'TRAUMA',
        'label': 'Severe Polytrauma / Hemorrhagic Shock',
        'window_name': 'Trauma Golden Hour Window',
        'max_window_mins': 60,    # Classic Golden Hour for damage control surgery
        'target_window_mins': 45,
        'required_service_keywords': ['trauma', 'surgery', 'ortho', 'neurosurgery', 'emergency surgery'],
        'required_facility_keywords': ['operating room', 'trauma bay', 'blood bank', 'resuscitation', 'surgical or'],
        'required_specialist': 'trauma_surgery',
        'urgency': 'EMERGENCY',
        'patterns': [
            r'polytrauma',
            r'severe[\s\-]+(mva|vehicular[\s\-]+accident|collision)',
            r'blunt[\s\-]+abdominal[\s\-]+trauma',
            r'hemorrhagic[\s\-]+shock',
            r'traumatic[\s\-]+brain[\s\-]+injury',
            r'\btbi\b',
            r'flail[\s\-]+chest',
            r'gunshot[\s\-]+wound',
            r'gsw',
            r'stab[\s\-]+wound',
            r'unstable[\s\-]+pelvic[\s\-]+fracture',
            r'gcs\s*[\<:]\s*[3-8]\b',
            r'fast[\s\-]+positive'
        ]
    },
    'SEPSIS': {
        'code': 'SEPSIS',
        'label': 'Severe Sepsis / Septic Shock',
        'window_name': 'Surviving Sepsis Hour-1 Bundle Window',
        'max_window_mins': 60,
        'target_window_mins': 45,
        'required_service_keywords': ['critical care', 'internal medicine', 'infectious disease', 'icu'],
        'required_facility_keywords': ['icu', 'intensive care', 'ventilator', 'central line'],
        'required_specialist': 'critical_care_icu',
        'urgency': 'EMERGENCY',
        'patterns': [
            r'septic[\s\-]+shock',
            r'severe[\s\-]+sepsis',
            r'refractory[\s\-]+hypotension',
            r'lactate[\s\-]?[:=]?\s*[4-9]\b',
            r'lactate[\s\-]?[:=]?\s*\d{2}',
            r'vasopressor[\s\-]+support',
            r'bacteremia.*shock',
            r'urosepsis.*hypotensive',
            r'mrs\s+shock'
        ]
    },
    'RESPIRATORY_FAILURE': {
        'code': 'RESPIRATORY_FAILURE',
        'label': 'Acute Respiratory Distress / Tension Pneumothorax',
        'window_name': 'Definitive Airway / Decompression Window',
        'max_window_mins': 45,
        'target_window_mins': 30,
        'required_service_keywords': ['pulmonary', 'pulmonology', 'critical care', 'thoracic'],
        'required_facility_keywords': ['icu', 'mechanical ventilator', 'airway'],
        'required_specialist': 'pulmonary_critical_care',
        'urgency': 'EMERGENCY',
        'patterns': [
            r'tension[\s\-]+pneumothorax',
            r'respiratory[\s\-]+arrest',
            r'acute[\s\-]+respiratory[\s\-]+distress',
            r'\bards\b',
            r'impending[\s\-]+respiratory[\s\-]+failure',
            r'severe[\s\-]+hypoxemia',
            r'stridor.*respiratory[\s\-]+fatigue',
            r'intubated.*failing[\s\-]+ventilation'
        ]
    }
}

def extract_clinical_syndrome(clinical_text):
    if not clinical_text:
        return {
            'detected': False,
            'syndrome': None,
            'label': 'General Clinical Condition',
            'time_window_mins': 180,
            'target_window_mins': 120,
            'window_name': 'Standard Urgent Transfer Window',
            'required_specialist': None,
            'required_service_keywords': [],
            'required_facility_keywords': [],
            'urgency_override': None,
            'extracted_signals': []
        }

    text = str(clinical_text).lower()
    detected_syndromes = []

    for syndrome_code, config in EMERGENCY_SYNDROMES.items():
        matched_signals = []
        for pat in config['patterns']:
            if re.search(pat, text, flags=re.IGNORECASE):
                matched_signals.append(pat)

        if matched_signals:
            detected_syndromes.append({
                'syndrome': syndrome_code,
                'label': config['label'],
                'time_window_mins': config['max_window_mins'],
                'target_window_mins': config['target_window_mins'],
                'window_name': config['window_name'],
                'required_specialist': config['required_specialist'],
                'required_service_keywords': config['required_service_keywords'],
                'required_facility_keywords': config['required_facility_keywords'],
                'urgency_override': config['urgency'],
                'signal_count': len(matched_signals),
                'extracted_signals': matched_signals
            })

    if not detected_syndromes:
        return {
            'detected': False,
            'syndrome': None,
            'label': 'General Clinical Condition',
            'time_window_mins': 180,
            'target_window_mins': 120,
            'window_name': 'Standard Urgent Transfer Window',
            'required_specialist': None,
            'required_service_keywords': [],
            'required_facility_keywords': [],
            'urgency_override': None,
            'extracted_signals': []
        }

    detected_syndromes.sort(key=lambda s: (-s['signal_count'], s['time_window_mins']))
    top = detected_syndromes[0]
    top['detected'] = True
    return top
