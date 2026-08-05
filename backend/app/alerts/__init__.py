"""Alert bus: rule evaluation, dedup/cooldown, dashboard feed, email digest."""

from app.alerts.emailer import build_digest, send_digest
from app.alerts.rules import evaluate_alerts

__all__ = ["build_digest", "evaluate_alerts", "send_digest"]
