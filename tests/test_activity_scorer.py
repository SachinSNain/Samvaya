import pytest
from datetime import datetime, timezone, timedelta
from src.activity_engine.signal_scorer import compute_activity_score

def test_permanent_signal_override():
    events = [
        {"event_type": "electricity_consumption_high", "event_timestamp": datetime.now(timezone.utc) - timedelta(days=5)},
        {"event_type": "licence_renewal", "event_timestamp": datetime.now(timezone.utc) - timedelta(days=10)},
        {"event_type": "closure_declaration", "event_timestamp": datetime.now(timezone.utc) - timedelta(days=2)}, # Permanent Negative
    ]
    
    result = compute_activity_score("test_ubid", events)
    
    assert result["activity_status"] == "CLOSED_CONFIRMED"
    assert result["raw_score"] == -1.0
    
def test_active_decay():
    # Only highly positive recent events
    events = [
        {"event_type": "electricity_consumption_high", "event_timestamp": datetime.now(timezone.utc) - timedelta(days=2)},
        {"event_type": "inspection_visit", "event_timestamp": datetime.now(timezone.utc) - timedelta(days=5)},
    ]
    
    result = compute_activity_score("test_ubid", events)
    
    assert result["activity_status"] == "ACTIVE"
    assert result["raw_score"] > 0.4
