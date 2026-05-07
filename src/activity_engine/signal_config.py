"""
activity_engine/signal_config.py
Central configuration for all signal types.
Modify weights and half-lives here to tune the activity classifier.
"""
import math

SIGNAL_WEIGHTS = {
    "electricity_consumption_high": +0.90,
    "water_consumption_high": +0.70,
    "licence_renewal": +0.80,
    "inspection_visit": +0.70,
    "compliance_filing": +0.75,
    "administrative_update": +0.40,
    "electricity_consumption_low": -0.50,
    "renewal_overdue": -0.40,
    "closure_declaration": -1.00,   # Permanent — no decay
    "licence_cancellation": -0.90,   # Permanent — no decay
}

SIGNAL_HALF_LIVES = {
    "electricity_consumption_high": 45,
    "water_consumption_high": 45,
    "licence_renewal": 365,
    "inspection_visit": 180,
    "compliance_filing": 270,
    "administrative_update": 90,
    "electricity_consumption_low": 30,
    "renewal_overdue": 180,
    "closure_declaration": None,   # None = permanent, never decays
    "licence_cancellation": None,
}

PERMANENT_SIGNALS = {"closure_declaration", "licence_cancellation"}

# Activity score thresholds
THRESHOLD_ACTIVE = +0.4
THRESHOLD_DORMANT_LOW = -0.2

# NIC codes with seasonal patterns — adjust active/dormant boundary
SEASONAL_NIC_CODES = {
    # Fireworks / basic chemicals
    "24": {"active_months": [10, 11, 12, 1, 2, 3]},
    "10": {"active_months": [10, 11, 12, 9]},      # Food (festive season peak)
    "14": {"active_months": [6, 7, 8, 9, 10, 11]},   # Apparel (export season)
}


def compute_decay(half_life_days: int | None, days_since: int) -> float:
    """Returns e^(-λ * days) where λ = ln(2) / half_life."""
    if half_life_days is None:
        return 1.0  # Permanent signal — no decay
    lambda_val = math.log(2) / half_life_days
    return math.exp(-lambda_val * days_since)
