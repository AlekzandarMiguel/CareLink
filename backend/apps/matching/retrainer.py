import os
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from django.conf import settings
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from xgboost import XGBClassifier

FEATURE_NAMES = [
    'service_match',
    'facility_match',
    'road_distance_km',
    'travel_time_mins',
    'urgency_weight',
    'mews_severity',
    'effective_bed_ratio',
    'effective_icu_ratio',
    'inbound_in_transit',
    'historical_acceptance',
    'specialist_on_duty',
    'window_compliance'
]

def generate_enhanced_training_data(n_samples=4000, random_seed=42):
    """
    Generates synthetic training dataset modeling realistic clinical triage scenarios
    with MEWS vital severity, real road travel time, specialist shifts, and golden hour windows.
    """
    np.random.seed(random_seed)

    service_match = np.random.choice([1, 0], size=n_samples, p=[0.75, 0.25])
    facility_match = np.random.choice([1, 0], size=n_samples, p=[0.80, 0.20])
    
    # Road distance
    road_distance_km = np.random.exponential(scale=22.0, size=n_samples) + np.random.uniform(2.0, 8.0, size=n_samples)
    road_distance_km = np.clip(road_distance_km, 1.5, 160.0)

    # Travel time minutes
    travel_time_mins = road_distance_km * np.random.uniform(1.35, 2.4, size=n_samples)
    travel_time_mins = np.clip(travel_time_mins, 5.0, 240.0)

    # Urgency (1=Routine, 2=Urgent, 3=Emergency)
    urgency_weight = np.random.choice([1, 2, 3], size=n_samples, p=[0.45, 0.35, 0.20])
    
    # MEWS severity score (0 to 12)
    mews_severity = np.random.choice(
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 
        size=n_samples, 
        p=[0.30, 0.20, 0.15, 0.12, 0.08, 0.05, 0.04, 0.03, 0.015, 0.01, 0.005]
    )

    # Inbound transfers currently in transit to this hospital
    inbound_in_transit = np.random.choice([0, 1, 2, 3, 4, 5], size=n_samples, p=[0.45, 0.25, 0.15, 0.08, 0.05, 0.02])

    # Effective capacity ratios
    base_bed_ratio = np.random.beta(a=2.5, b=4.5, size=n_samples)
    effective_bed_ratio = np.clip(base_bed_ratio - (inbound_in_transit * 0.05), 0.0, 1.0)

    base_icu_ratio = np.random.beta(a=2.0, b=5.0, size=n_samples)
    effective_icu_ratio = np.clip(base_icu_ratio - (inbound_in_transit * 0.08), 0.0, 1.0)

    # Historical acceptance
    historical_acceptance = np.random.uniform(0.60, 0.98, size=n_samples)

    # Specialist on-duty flag (0 or 1)
    specialist_on_duty = np.random.choice([1, 0], size=n_samples, p=[0.72, 0.28])

    # Time Window compliance (1 = within safe window, 0 = exceeded cutoff)
    critical_cases = (urgency_weight == 3) | (mews_severity >= 5)
    max_allowable_mins = np.where(critical_cases, np.random.choice([60, 90, 180], size=n_samples), 240)
    window_compliance = (travel_time_mins <= max_allowable_mins).astype(int)

    # Balanced logit function
    logit = (
        3.0 * service_match +
        1.1 * facility_match -
        0.04 * road_distance_km -
        0.03 * travel_time_mins +
        2.0 * effective_bed_ratio +
        1.6 * (historical_acceptance - 0.70) -
        0.55 * inbound_in_transit +
        0.9 * specialist_on_duty +
        1.4 * window_compliance -
        0.7
    )

    # Critical Emergency interactions
    logit += 2.2 * effective_icu_ratio * critical_cases
    logit -= 0.04 * travel_time_mins * critical_cases
    logit -= 2.5 * (effective_icu_ratio == 0.0) * critical_cases
    logit -= 2.0 * (window_compliance == 0) * critical_cases

    prob = 1.0 / (1.0 + np.exp(-logit))
    prob = np.clip(prob, 0.05, 0.98)
    target = (np.random.uniform(0, 1, size=n_samples) < prob).astype(int)
    
    target[service_match == 0] = 0
    target[critical_cases & (effective_icu_ratio == 0.0)] = 0

    return pd.DataFrame({
        'service_match': service_match,
        'facility_match': facility_match,
        'road_distance_km': road_distance_km,
        'travel_time_mins': travel_time_mins,
        'urgency_weight': urgency_weight,
        'mews_severity': mews_severity,
        'effective_bed_ratio': effective_bed_ratio,
        'effective_icu_ratio': effective_icu_ratio,
        'inbound_in_transit': inbound_in_transit,
        'historical_acceptance': historical_acceptance,
        'specialist_on_duty': specialist_on_duty,
        'window_compliance': window_compliance,
        'target': target
    })

def train_and_export_model(model_save_path=None):
    if model_save_path is None:
        model_save_path = getattr(settings, 'ML_MODEL_PATH', None)
        if not model_save_path:
            base_dir = getattr(settings, 'BASE_DIR', Path(__file__).resolve().parent.parent.parent)
            model_save_path = os.path.join(base_dir, 'ml_models', 'hospital_matcher_xgb.joblib')

    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)

    df = generate_enhanced_training_data(n_samples=4000)
    X = df[FEATURE_NAMES]
    y = df['target']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=130,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        eval_metric='logloss'
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics = {
        'accuracy': round(float(accuracy_score(y_test, y_pred)), 4),
        'precision': round(float(precision_score(y_test, y_pred)), 4),
        'recall': round(float(recall_score(y_test, y_pred)), 4),
        'f1_score': round(float(f1_score(y_test, y_pred)), 4),
        'roc_auc': round(float(roc_auc_score(y_test, y_prob)), 4),
        'samples': len(df),
        'features': FEATURE_NAMES,
        'model_path': model_save_path
    }

    joblib.dump(model, model_save_path)
    return metrics
