import os
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from xgboost import XGBClassifier

def generate_synthetic_dataset(n_samples=3000, random_seed=42):
    np.random.seed(random_seed)
    
    service_match = np.random.choice([1, 0], size=n_samples, p=[0.75, 0.25])
    facility_match = np.random.choice([1, 0], size=n_samples, p=[0.80, 0.20])
    distance_km = np.random.exponential(scale=18.0, size=n_samples) + np.random.uniform(1.0, 5.0, size=n_samples)
    distance_km = np.clip(distance_km, 1.0, 150.0)
    urgency_weight = np.random.choice([1, 2, 3], size=n_samples, p=[0.5, 0.3, 0.2])
    bed_ratio = np.random.beta(a=2, b=5, size=n_samples)
    icu_ratio = np.random.beta(a=1.5, b=4, size=n_samples)
    historical_acc = np.random.uniform(0.65, 0.98, size=n_samples)

    logit = (
        3.5 * service_match +
        1.8 * facility_match -
        0.045 * distance_km +
        1.2 * bed_ratio +
        (1.5 * icu_ratio * (urgency_weight == 3)) +
        2.0 * (historical_acc - 0.5) -
        2.2
    )
    logit -= 0.02 * distance_km * (urgency_weight == 3)

    prob = 1.0 / (1.0 + np.exp(-logit))
    target = (np.random.uniform(0, 1, size=n_samples) < prob).astype(int)
    target[service_match == 0] = 0

    return pd.DataFrame({
        'service_match': service_match,
        'facility_match': facility_match,
        'distance_km': distance_km,
        'urgency_weight': urgency_weight,
        'bed_ratio': bed_ratio,
        'icu_ratio': icu_ratio,
        'historical_acc': historical_acc,
        'successful_match': target
    })

def train_and_save_model():
    print("="*60)
    print("CareLink XGBoost Hospital Matching Model Training Pipeline")
    print("="*60)

    df = generate_synthetic_dataset(n_samples=3000)
    print(f"Dataset generated: {len(df)} samples.")

    feature_cols = [
        'service_match', 'facility_match', 'distance_km',
        'urgency_weight', 'bed_ratio', 'icu_ratio', 'historical_acc'
    ]

    X = df[feature_cols]
    y = df['successful_match']

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

    model = XGBClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        eval_metric='logloss'
    )

    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_pred_proba)

    print("Test Set Evaluation Metrics:")
    print(f"Accuracy:  {acc*100:.2f}%")
    print(f"Precision: {prec*100:.2f}%")
    print(f"Recall:    {rec*100:.2f}%")
    print(f"F1-Score:  {f1*100:.2f}%")
    print(f"ROC-AUC:   {auc:.4f}")

    save_dir = Path(os.getcwd()) / 'ml' / 'models'
    save_dir.mkdir(parents=True, exist_ok=True)
    model_path = save_dir / 'xgboost_hospital_matcher.joblib'
    joblib.dump(model, model_path)
    print(f"Model saved to: {model_path}")
    print("="*60)

if __name__ == '__main__':
    train_and_save_model()
