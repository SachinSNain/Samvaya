import pytest
import numpy as np
from src.entity_resolution.scorer import score_pair
import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import BaseEstimator, ClassifierMixin

# Mock classifier
class MockLGBM(BaseEstimator, ClassifierMixin):
    def predict_proba(self, X):
        # Always return 0.99 for class 1
        return np.array([[0.01, 0.99]])
    def predict(self, X):
        return np.array([1])
        
class MockCalibrated(BaseEstimator, ClassifierMixin):
    def predict_proba(self, X):
        return np.array([[0.05, 0.95]])

# Mock TreeExplainer
class MockExplainer:
    def __init__(self, model):
        pass
    def __call__(self, X):
        class MockResult:
            values = np.zeros((1, 13))
            feature_names = [f"F{str(i).zfill(2)}" for i in range(1, 14)]
        return MockResult()
    def shap_values(self, X):
        return [np.zeros((1, 13)), np.zeros((1, 13))]

# Patch shap
import shap
shap.TreeExplainer = MockExplainer

def test_pan_hard_rule():
    features = {f"F{str(i).zfill(2)}": 1.0 for i in range(1, 14)}
    features["F04"] = -1.0  # PAN Mismatch
    
    calib = MockCalibrated()
    base = MockLGBM()
    
    result = score_pair(features, calib, base)
    
    # The hard rule should force the score to 0.0 despite the mock model predicting 0.95
    assert result["calibrated_score"] == 0.0
    assert result["decision"] == "KEEP_SEPARATE"

def test_auto_link():
    features = {f"F{str(i).zfill(2)}": 1.0 for i in range(1, 14)}
    features["F04"] = 1.0  # PAN Match
    
    calib = MockCalibrated()
    base = MockLGBM()
    
    result = score_pair(features, calib, base)
    
    # Assuming threshold is 0.95 and mock returns 0.95
    assert result["calibrated_score"] == 0.95
    assert result["decision"] == "AUTO_LINK"
