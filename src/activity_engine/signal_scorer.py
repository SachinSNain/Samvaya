"""
activity_engine/signal_scorer.py
Evaluates event timelines and generates activity classifications.
"""
from datetime import datetime, timezone
import math
from .signal_config import (
    SIGNAL_WEIGHTS, SIGNAL_HALF_LIVES, PERMANENT_SIGNALS,
    compute_decay, THRESHOLD_ACTIVE, THRESHOLD_DORMANT_LOW
)

LOOKBACK_DAYS = 365


def compute_activity_score(
        ubid: str,
        events: list,
        reference_date: datetime = None) -> dict:
    """
    events: list of dicts {event_type, event_timestamp, source_system, payload}
    Returns: {raw_score, activity_status, evidence, event_count, lookback_days, computed_at}
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    # Check for hard permanent signals first
    if reference_date.tzinfo is None:
        reference_date = reference_date.replace(tzinfo=timezone.utc)
    for event in events:
        if event["event_type"] in PERMANENT_SIGNALS:
            ts_val = event["event_timestamp"]
            if isinstance(ts_val, str):
                event_ts = datetime.fromisoformat(ts_val)
            else:
                event_ts = ts_val
            if event_ts.tzinfo is None:
                event_ts = event_ts.replace(tzinfo=timezone.utc)
            days_since = max(0, (reference_date - event_ts).days)
            return {
                "raw_score": -1.0,
                "activity_status": "CLOSED_CONFIRMED",
                "evidence": [{
                    "event_type": event["event_type"],
                    "event_timestamp": str(event["event_timestamp"]),
                    "source_system": event.get("source_system", "unknown"),
                    "weight": SIGNAL_WEIGHTS[event["event_type"]],
                    "decay": 1.0,
                    "contribution": SIGNAL_WEIGHTS[event["event_type"]],
                    "note": "PERMANENT_SIGNAL",
                    "days_since": days_since
                }],
                "event_count": len(events),
                "lookback_days": LOOKBACK_DAYS,
                "computed_at": reference_date.isoformat()
            }

    # Filter to lookback window
    cutoff = reference_date.timestamp() - (LOOKBACK_DAYS * 86400)
    recent_events = []

    for e in events:
        ts_val = e["event_timestamp"]
        if isinstance(ts_val, str):
            ts = datetime.fromisoformat(ts_val)
        else:
            ts = ts_val

        if ts.timestamp() > cutoff:
            recent_events.append(e)

    total_score = 0.0
    evidence = []

    for event in recent_events:
        event_type = event["event_type"]
        if event_type not in SIGNAL_WEIGHTS:
            try:
                from src.llm_router import route, TaskType
                known_types = list(SIGNAL_WEIGHTS.keys())
                mapped = route(
                    TaskType.EVENT_CLASSIFIER,
                    f"Map this event to the closest match from: {known_types}\n"
                    f"Unknown event: '{event_type}'\n"
                    "Return ONLY the matched event type string, nothing else.",
                    max_tokens=30,
                ).strip().strip('"')
                event_type = mapped if mapped in SIGNAL_WEIGHTS else event_type
            except Exception:
                pass
            if event_type not in SIGNAL_WEIGHTS:
                continue

        weight = SIGNAL_WEIGHTS[event_type]
        half_life = SIGNAL_HALF_LIVES.get(event_type)

        ts_val = event["event_timestamp"]
        if isinstance(ts_val, str):
            event_ts = datetime.fromisoformat(ts_val)
        else:
            event_ts = ts_val

        if event_ts.tzinfo is None:
            event_ts = event_ts.replace(tzinfo=timezone.utc)
        else:
            event_ts = event_ts.astimezone(timezone.utc)

        if reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)

        days_since = (reference_date - event_ts).days
        days_since = max(0, days_since)

        decay = compute_decay(half_life, days_since)
        contribution = weight * decay
        total_score += contribution

        evidence.append({
            "event_type": event_type,
            "event_timestamp": str(event["event_timestamp"]),
            "source_system": event.get("source_system", "unknown"),
            "weight": weight,
            "decay": round(decay, 4),
            "contribution": round(contribution, 4),
            "days_since": days_since
        })

    # Normalise to [-1, +1] using sigmoid-like transform
    normalised_score = 2 / (1 + math.exp(-total_score)) - 1

    # Classify
    if normalised_score > THRESHOLD_ACTIVE:
        status = "ACTIVE"
    elif normalised_score >= THRESHOLD_DORMANT_LOW:
        status = "DORMANT"
    else:
        status = "CLOSED_SUSPECTED"

    # Sort evidence by |contribution| descending for display
    evidence.sort(key=lambda x: abs(x["contribution"]), reverse=True)

    return {
        "raw_score": round(normalised_score, 4),
        "activity_status": status,
        "evidence": evidence,
        "event_count": len(recent_events),
        "lookback_days": LOOKBACK_DAYS,
        "computed_at": reference_date.isoformat()
    }
