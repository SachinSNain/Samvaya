"""
entity_resolution/scorer.py
Loads trained LightGBM model, scores pairs, applies PAN hard rule, and routes to decisions.
"""
import os
import warnings
import pickle
import numpy as np
import lightgbm as lgb
import shap

FEATURE_ORDER = [
    "F01", "F02", "F03", "F04", "F05", "F06", "F07",
    "F08", "F09", "F10", "F11", "F12", "F13", "F14",
]

THRESHOLD_AUTO_LINK = float(os.getenv("THRESHOLD_AUTO_LINK", "0.95"))
THRESHOLD_REVIEW = float(os.getenv("THRESHOLD_REVIEW", "0.75"))
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def features_to_array(feature_dict: dict) -> np.ndarray:
    """Converts feature dict to numpy array in consistent order. None -> np.nan."""
    return np.array([
        feature_dict.get(f, np.nan) if feature_dict.get(f) is not None else np.nan
        for f in FEATURE_ORDER
    ], dtype=np.float32)


def load_models():
    """
    Loads calibrated_model, base lgbm_model, and pre-builds the SHAP TreeExplainer.

    Building the explainer once here (rather than inside score_pair) avoids
    re-constructing the internal tree structure on every scored pair, which was
    the dominant cost when running 500k+ candidate pairs.
    """
    calib_path = os.path.join(MODEL_DIR, "calibrated_model.pkl")
    lgbm_path = os.path.join(MODEL_DIR, "lgbm_model.pkl")

    with open(calib_path, "rb") as f:
        calibrated_model = pickle.load(f)
    with open(lgbm_path, "rb") as f:
        lgbm_model = pickle.load(f)

    # Build explainer once; suppress noisy version-skew warnings from shap.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        shap_explainer = shap.TreeExplainer(lgbm_model)

    return calibrated_model, lgbm_model, shap_explainer


def score_pair(
    feature_dict: dict,
    calibrated_model,
    lgbm_model,
    shap_explainer=None,
    rec_a: dict = None,
    rec_b: dict = None,
) -> dict:
    """
    Returns confidence score, routing decision, and SHAP values for a candidate pair.

    Args:
        feature_dict:      Feature vector as returned by extract_features().
        calibrated_model:  Calibrated probability model (sklearn-compatible).
        lgbm_model:        Raw LightGBM booster (used only for SHAP).
        shap_explainer:    Pre-built shap.TreeExplainer.  Pass the value returned
                           by load_models() so it is NOT rebuilt on every call.
                           If None (backward-compat / tests), a one-off explainer
                           is built locally — but only when SHAP would actually run.
        rec_a, rec_b:      Raw normalised records; only used for the optional LLM
                           reviewer-explanation path.
    """
    feature_array = features_to_array(feature_dict).reshape(1, -1)

    # Confidence score from calibrated model
    calibrated_score = float(
        calibrated_model.predict_proba(feature_array)[0][1])

    # PAN hard rule: if both records have PAN and they MISMATCH -> force Keep Separate
    pan_hard_rule = False
    if feature_dict.get("F04") == -1.0:
        calibrated_score = 0.0
        pan_hard_rule = True

    # Routing decision
    if calibrated_score >= THRESHOLD_AUTO_LINK:
        decision = "AUTO_LINK"
    elif calibrated_score >= THRESHOLD_REVIEW:
        decision = "REVIEW"
    else:
        decision = "KEEP_SEPARATE"

    # SHAP only for pairs that need explanation (REVIEW or AUTO_LINK).
    # KEEP_SEPARATE pairs (the vast majority in a 500k+ run) skip this block entirely.
    shap_dict = {}
    if decision in ("AUTO_LINK", "REVIEW"):
        # Use the pre-built explainer when available; fall back for tests / ad-hoc calls.
        explainer = shap_explainer
        if explainer is None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                explainer = shap.TreeExplainer(lgbm_model)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            shap_values = explainer.shap_values(feature_array)

        # LightGBM < 4.0 returns list[class_0, class_1]; >= 4.0 returns 3D (n, feat, classes)
        if isinstance(shap_values, list):
            shap_for_match = shap_values[1][0]
        elif hasattr(shap_values, "ndim") and shap_values.ndim == 3:
            shap_for_match = shap_values[0, :, 1]
        else:
            shap_for_match = shap_values[0]

        shap_dict = {
            feat: round(float(shap_for_match[i]), 4)
            for i, feat in enumerate(FEATURE_ORDER)
        }
    
    reviewer_explanation = None
    # Skip LLM reviewer explanation during bulk pipeline runs (enable via ENABLE_REVIEW_LLM=true)
    if decision == "REVIEW" and rec_a and rec_b and os.getenv("ENABLE_REVIEW_LLM", "false").lower() == "true":
        try:
            from src.llm_router import route, TaskType
            prompt = (
                f"Two Karnataka business records scored {calibrated_score:.0%} match confidence.\n\n"
                f"Record A: name='{rec_a.get('raw_name')}', "
                f"address='{rec_a.get('raw_address')}', "
                f"PAN={rec_a.get('pan', 'N/A')}\n"
                f"Record B: name='{rec_b.get('raw_name')}', "
                f"address='{rec_b.get('raw_address')}', "
                f"PAN={rec_b.get('pan', 'N/A')}\n\n"
                f"Key signals: name_sim={feature_dict.get('F01', 0):.2f}, "
                f"pan_match={feature_dict.get('F04')}, "
                f"phone_match={feature_dict.get('F09')}\n\n"
                "Write 2 sentences: (1) strongest evidence they ARE the same business, "
                "(2) strongest evidence they are NOT. Be specific."
            )
            reviewer_explanation = route(
                TaskType.REVIEWER_EXPLANATION, prompt, max_tokens=150
            )
        except Exception:
            reviewer_explanation = None

    return {
        "calibrated_score": calibrated_score,
        "decision": decision,
        "shap_values": shap_dict,
        "pan_hard_rule_applied": pan_hard_rule,
        "reviewer_explanation": reviewer_explanation
    }
