"""
scripts/train_model.py
Trains the LightGBM classifier for entity resolution using the synthetic ground truth data.
Outputs models to src/entity_resolution/models/
"""
import os
import sys
import pandas as pd
import numpy as np
import lightgbm as lgb
import pickle
import logging
from pathlib import Path
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, precision_recall_curve

# Ensure the src module is in the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.entity_resolution.scorer import FEATURE_ORDER
from src.entity_resolution.feature_extractor import extract_features
from src.normalisation.standardiser import standardise_record


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_raw_records() -> dict:
    """Load and standardise all raw department records for feature extraction."""
    raw_dir = Path("data/raw")
    records = []

    # Read all 4 department files
    for file_name in [
        "shop_establishment.csv",
        "factories.csv",
        "labour.csv",
            "kspcb.csv"]:
        file_path = raw_dir / file_name
        if not file_path.exists():
            continue

        df = pd.read_csv(file_path)
        source_system = file_name.replace(".csv", "")

        # Inject source system into dicts and convert NaN to None
        for record in df.replace({np.nan: None}).to_dict("records"):
            record["source_system"] = source_system
            records.append(record)

    logger.info(f"Loaded {len(records)} raw records.")

    # Standardise them (skip Nominatim geocoding during bulk training run to
    # save time)
    standardised_dict = {}
    for rec in records:
        std_rec = standardise_record(rec, skip_geocoding=True)
        standardised_dict[std_rec["record_id"]] = std_rec

    return standardised_dict


def train():
    logger.info("Starting model training pipeline...")

    # 1. Load labelled pairs
    pairs_path = Path("data/ground_truth/labelled_pairs.csv")
    if not pairs_path.exists():
        logger.error(
            f"{pairs_path} not found. Run generate_synthetic_data.py first.")
        return

    pairs_df = pd.read_csv(pairs_path)
    logger.info(f"Loaded {len(pairs_df)} labelled pairs.")

    # 2. Load all records to extract features
    record_lookup = load_raw_records()

    # 3. Extract features for all pairs
    logger.info("Extracting features for candidate pairs...")
    X_data = []
    y_data = []

    for _, row in pairs_df.iterrows():
        id_a, id_b = row["record_a_id"], row["record_b_id"]
        source_a, source_b = row["source_a"], row["source_b"]
        label = row["label"]

        rec_a = record_lookup.get(f"{source_a}:{id_a}")
        rec_b = record_lookup.get(f"{source_b}:{id_b}")

        if not rec_a or not rec_b:
            logger.warning(
                f"Could not find records for pair {id_a} - {id_b}. Skipping.")
            continue

        features = extract_features(rec_a, rec_b)

        # Convert to ordered array
        feature_array = [
            features.get(f, np.nan) if features.get(f) is not None else np.nan
            for f in FEATURE_ORDER
        ]

        X_data.append(feature_array)
        y_data.append(label)

    X = np.array(X_data, dtype=np.float32)
    y = np.array(y_data, dtype=np.int32)

    logger.info(f"Feature matrix shape: {X.shape}")

    # 4. Train LightGBM model
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42)

    # Detect LightGBM OpenCL GPU availability by doing a tiny test fit
    _gpu_available = False
    try:
        import numpy as _np
        _test = lgb.LGBMClassifier(device="gpu", n_estimators=1, verbose=-1)
        _test.fit(
            _np.array([[0.0], [1.0], [0.0], [1.0]]),
            _np.array([0, 1, 0, 1])
        )
        _gpu_available = True
    except Exception:
        pass

    if _gpu_available:
        logger.info("LightGBM OpenCL GPU available — enabling GPU training.")
    else:
        logger.info("LightGBM GPU unavailable — using CPU training.")

    lgbm_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "min_data_in_leaf": 20,
        "n_estimators": 300,
        "verbose": -1,
        "random_state": 42,
        **({"device": "gpu", "gpu_platform_id": 0, "gpu_device_id": 0} if _gpu_available else {}),
    }

    logger.info("Training LightGBM model...")
    base_lgbm = lgb.LGBMClassifier(**lgbm_params)

    # 5. Calibrate via Platt Scaling
    logger.info("Calibrating model using Platt Scaling...")
    calibrated_model = CalibratedClassifierCV(
        base_lgbm, method="sigmoid", cv=5)
    calibrated_model.fit(X_train, y_train)

    # 6. Evaluate
    val_preds = calibrated_model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, val_preds)

    # Calculate F1 score at THRESHOLD_AUTO_LINK (0.95)
    threshold = float(os.getenv("THRESHOLD_AUTO_LINK", "0.95"))
    y_pred_binary = (val_preds >= threshold).astype(int)
    f1 = f1_score(y_val, y_pred_binary)

    logger.info(f"Validation AUC: {auc:.4f}")
    logger.info(f"F1 at {threshold} threshold: {f1:.4f}")

    # 7. MLflow logging (Optional, wraps silently if MLflow not available)
    try:
        import mlflow
        import mlflow.sklearn
        mlflow.set_tracking_uri(
            os.getenv(
                "MLFLOW_TRACKING_URI",
                "http://localhost:5000"))
        with mlflow.start_run():
            mlflow.log_params(lgbm_params)
            mlflow.log_metric("val_auc", auc)
            mlflow.log_metric("val_f1", f1)
            mlflow.sklearn.log_model(calibrated_model, "calibrated_model")
            logger.info("Logged metrics and model to MLflow.")
    except ImportError:
        logger.warning("MLflow not installed. Skipping MLflow logging.")
    except Exception as e:
        logger.warning(f"MLflow logging failed (is server running?): {e}")

    # 8. Save models locally
    model_dir = Path("src/entity_resolution/models")
    model_dir.mkdir(parents=True, exist_ok=True)

    calib_path = model_dir / "calibrated_model.pkl"
    lgbm_path = model_dir / "lgbm_model.pkl"

    with open(calib_path, "wb") as f:
        pickle.dump(calibrated_model, f)

    base_model = calibrated_model.calibrated_classifiers_[0].estimator
    with open(lgbm_path, "wb") as f:
        pickle.dump(base_model, f)

    # Save metrics so admin endpoint can serve real numbers
    import json
    from datetime import datetime, timezone
    metrics = {
        "val_auc": round(auc, 4),
        "val_f1": round(f1, 4),
        "threshold_auto_link": threshold,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "1.0.0",
        "train_size": len(X_train),
        "val_size": len(X_val),
    }
    with open(model_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"Models and metrics saved to {model_dir}")


if __name__ == "__main__":
    train()
