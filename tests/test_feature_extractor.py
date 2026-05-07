import pytest
from src.entity_resolution.feature_extractor import extract_features

def test_feature_extraction():
    rec_a = {
        "canonical_name": "Sree Balaji Traders",
        "pan": "ABCDE1234F",
        "pin_code": "560001",
        "nic_code": "1011",
        "source_system": "shop_establishment"
    }
    rec_b = {
        "canonical_name": "Balaji Traders Sree",
        "pan": "ABCDE1234F",
        "pin_code": "560002",  # adjacent
        "nic_code": "1012",   # 2-digit match
        "source_system": "factories"
    }
    
    features = extract_features(rec_a, rec_b)
    
    # F01 Jaro-Winkler should be decent but not 1.0
    assert 0.6 < features["F01"] < 1.0
    # F02 Token Set Ratio should be 1.0 (100) because words are identical just swapped
    assert features["F02"] == 1.0
    # F04 PAN match
    assert features["F04"] == 1.0
    # F06 Pincode mismatch (but no adjacency map in test context, so likely 0.0 unless we mock PIN_ADJACENCY)
    # F10 NIC 2-digit match
    assert features["F10"] == 0.7
    # F12 Same source flag
    assert features["F12"] == 0.0

def test_missing_features():
    rec_a = {"canonical_name": "Test", "source_system": "sys1"}
    rec_b = {"canonical_name": "Test", "source_system": "sys2"}
    
    features = extract_features(rec_a, rec_b)
    
    # F04 PAN should be 0.0 (missing)
    assert features["F04"] == 0.0
    assert features["F01"] == 1.0
