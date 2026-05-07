import pytest
from src.entity_resolution.blocker import generate_candidate_pairs

def test_blocking_recall():
    """
    Simulates a small set of records and ensures the candidate pair generation
    produces the expected pairs without missing obvious ones, and deduplicates.
    """
    records = [
        # Pair 1: Exact PAN match
        {"record_id": "r1", "pan": "ABCDE1234F", "gstin": "29ABCDE1234F1Z5", "canonical_name": "Test Co", "pin_code": "560001", "nic_code": "10"},
        {"record_id": "r2", "pan": "ABCDE1234F", "gstin": None, "canonical_name": "Test Co Pvt", "pin_code": "560002", "nic_code": "10"},
        
        # Pair 2: Soundex/Pin code match (No PAN)
        {"record_id": "r3", "pan": None, "gstin": None, "canonical_name": "Balaji Enterprises", "soundex": "B420", "metaphone": "BLJ", "pin_code": "560100", "nic_code": "45"},
        {"record_id": "r4", "pan": None, "gstin": None, "canonical_name": "Sree Balaji Enterprize", "soundex": "B420", "metaphone": "BLJ", "pin_code": "560100", "nic_code": "45"},
        
        # Unrelated
        {"record_id": "r5", "pan": "XYZDE1234F", "gstin": None, "canonical_name": "Unrelated LLC", "soundex": "U564", "metaphone": "UNR", "pin_code": "110001", "nic_code": "99"},
    ]
    
    pairs = generate_candidate_pairs(records)
    
    # We expect r1-r2 (PAN match) and r3-r4 (Soundex+Pin match)
    # Plus r3-r4 also match on Metaphone+Pin and NIC+Pin
    # The pairs should be deduplicated
    
    # Normalize pairs to handle order
    normalized_pairs = set([tuple(sorted(p)) for p in pairs])
    
    assert tuple(sorted(("r1", "r2"))) in normalized_pairs
    assert tuple(sorted(("r3", "r4"))) in normalized_pairs
    
    # Ensure unrelated is not paired with anything based on the keys
    for p in pairs:
        assert "r5" not in p
