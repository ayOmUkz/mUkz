"""The nightly email digest: one message, grouped by rule (plan §14).

Per-alert emails stay off by default — a digest respects the reader.
Sending is skipped (and says so) when SMTP is not configured; the SMTP
transport is injectable so tests never talk to a real server.
"""

from __future__ import annotations

import smtplib
from collections.abc import Callable
from datetime import date
from email.message import EmailMessage
from typing import Any

from app.config import Secrets

RULE_HEADINGS = {
    "extreme_print": "New extreme prints",
    "repeated_prints_zone": "Repeated prints at a level",
    "zone_notional_threshold": "Cumulative notional thresholds",
    "zone_reclaimed": "Zones reclaimed",
    "zone_broken": "Zones broken",
    "directional_signal": "Directional signals",
    "signal_invalidated": "Signals invalidated",
    "stale_signal": "Stale signals",
}


def build_digest(as_of: date, alerts: list[dict[str, Any]]) -> tuple[str, str]:
    """(subject, plain-text body) for the day's alerts."""
    subject = f"Dark Pool Digest {as_of.isoformat()} — {len(alerts)} alert(s)"
    if not alerts:
        return subject, "No alerts today.\n"
    lines: list[str] = [f"Dark Pool Intelligence Engine — {as_of.isoformat()}", ""]
    by_rule: dict[str, list[dict[str, Any]]] = {}
    for alert in alerts:
        by_rule.setdefault(alert["rule"], []).append(alert)
    for rule, rows in by_rule.items():
        lines.append(RULE_HEADINGS.get(rule, rule))
        lines.append("-" * len(RULE_HEADINGS.get(rule, rule)))
        for alert in rows:
            details = ", ".join(
                f"{key}={value}" for key, value in sorted(alert["payload"].items())
            )
            lines.append(f"  {alert['ticker']}: {details}")
        lines.append("")
    lines.append("Probabilities, not promises — check invalidation levels first.")
    return subject, "\n".join(lines) + "\n"


def send_digest(
    secrets: Secrets,
    subject: str,
    body: str,
    *,
    smtp_factory: Callable[..., Any] = smtplib.SMTP,
) -> dict[str, Any]:
    """Send the digest if SMTP is configured; otherwise report why not."""
    if not secrets.smtp_host or not secrets.alert_email_to or not secrets.alert_email_from:
        return {"sent": False, "reason": "smtp_not_configured"}
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = secrets.alert_email_from
    message["To"] = secrets.alert_email_to
    message.set_content(body)
    with smtp_factory(secrets.smtp_host, secrets.smtp_port) as smtp:
        smtp.starttls()
        if secrets.smtp_user and secrets.smtp_password:
            smtp.login(secrets.smtp_user, secrets.smtp_password.get_secret_value())
        smtp.send_message(message)
    return {"sent": True, "to": secrets.alert_email_to}
