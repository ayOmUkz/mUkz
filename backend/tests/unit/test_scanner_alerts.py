"""Scanner categories + alert rules on a seeded, controlled database."""

from datetime import UTC, date, datetime

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.alerts import build_digest, evaluate_alerts, send_digest
from app.api.main import app, get_engine, get_settings
from app.config import Secrets, Settings
from app.db import alerts as alerts_table
from app.db import candles, ensure_schema, make_engine, prints, signals, symbol_days
from app.db import zone_events as zone_events_table
from app.db import zones as zones_table
from app.scanner import scan

AS_OF = date(2026, 8, 5)
NOW = datetime(2026, 8, 5, 22, 0, tzinfo=UTC)
SETTINGS = Settings()


def insert_print(conn, ticker: str, *, size_class: str, size: int = 500_000,
                 price: float = 100.0, tracking_id: int = 1) -> None:
    executed = datetime(2026, 8, 5, 15, 0, tzinfo=UTC)
    conn.execute(prints.insert().values(
        ticker=ticker, executed_at=executed, created_at=executed,
        price=price, size=size, premium=price * size,
        report_delay_s=1.0, quality_flags=[], location_confidence="ok",
        ingested_at=NOW, size_class=size_class, character="routine_off_exchange",
        timing_bucket="morning", tracking_id=tracking_id,
    ))


def insert_zone(conn, ticker: str, *, as_of=AS_OF, wavg: float = 99.0,
                strength: float = 75.0, status: str = "respected",
                unique_days: int = 4, notional: float = 60_000_000.0) -> int:
    executed = datetime(2026, 8, 4, 15, 0, tzinfo=UTC)
    result = conn.execute(zones_table.insert().values(
        ticker=ticker, as_of_date=as_of, window_start=as_of, window_end=as_of,
        price_low=wavg - 0.5, price_high=wavg + 0.5, wavg_price=wavg,
        total_shares=1_000_000, total_notional=notional, print_count=6,
        unique_days=unique_days, first_print_at=executed, last_print_at=executed,
        pct_adv30=0.02, pct_dark_volume=0.5, tightness_atr=0.5,
        strength_score=strength, strength_class="strong", status=status,
        respected_touches=2, created_at=NOW,
    ))
    return int(result.inserted_primary_key[0])


def insert_signal(conn, ticker: str, *, as_of=AS_OF, classification: str,
                  dpss: float, confidence: float = 0.6,
                  supporting=None, contradicting=None, invalidation=None,
                  top_zone=None) -> None:
    conn.execute(signals.insert().values(
        ticker=ticker, as_of_date=as_of, classification=classification,
        confidence=confidence, dpss=dpss,
        sub_scores={"print": 60, "zone": 70, "direction": confidence * 100,
                    "relevance": 80, "quality": 90},
        evidence={"supporting": supporting or [], "contradicting": contradicting or [],
                  "groups": ["A", "B"]},
        invalidation=invalidation or [], top_zone=top_zone, available_at=NOW,
    ))


def insert_close(conn, ticker: str, close: float) -> None:
    ts = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)
    conn.execute(candles.insert().values(
        ticker=ticker, candle_size="1d", ts=ts,
        open=close, high=close + 1, low=close - 1, close=close, volume=1_000_000,
    ))
    conn.execute(symbol_days.insert().values(
        ticker=ticker, trading_date=AS_OF, atr14=2.0, minute_bars=0, updated_at=NOW,
    ))


def item(direction: int, weight: int, group: str = "A") -> dict:
    return {"id": f"e{group}{weight}", "group": group, "direction": direction,
            "weight": weight, "description": f"synthetic {group} item"}


@pytest.fixture()
def engine():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    with engine.begin() as conn:
        # ACC: strong accumulation story near price, with an extreme print today.
        acc_zone = {"wavg_price": 99.0, "price_low": 98.5, "price_high": 99.5,
                    "strength_score": 75.0, "strength_class": "strong",
                    "status": "respected", "unique_days": 4, "total_shares": 1_000_000,
                    "strength_components": {}}
        insert_signal(conn, "ACC", classification="probable_accumulation", dpss=72,
                      confidence=0.65,
                      supporting=[item(1, 2, "A"), item(1, 2, "B")],
                      contradicting=[item(-1, 1, "C")],
                      invalidation=[{"type": "daily_close_below", "level": 97.5}],
                      top_zone=acc_zone)
        zone_id = insert_zone(conn, "ACC")
        conn.execute(zone_events_table.insert().values(
            zone_id=zone_id, session_date=date(2026, 8, 4), event="reject", close=101.0,
        ))
        insert_close(conn, "ACC", 100.0)
        insert_print(conn, "ACC", size_class="extreme", tracking_id=11)

        # DST: distribution with a broken zone.
        dst_zone = {"wavg_price": 120.0, "price_low": 119.5, "price_high": 120.5,
                    "strength_score": 62.0, "strength_class": "strong",
                    "status": "broken", "unique_days": 3, "total_shares": 500_000,
                    "strength_components": {}}
        insert_signal(conn, "DST", classification="probable_distribution", dpss=65,
                      confidence=0.55, supporting=[],
                      contradicting=[item(-1, 2, "A"), item(-1, 2, "B")],
                      top_zone=dst_zone)
        insert_zone(conn, "DST", wavg=120.0, strength=62.0, status="broken",
                    unique_days=3, notional=10_000_000)

        # CON: meaningful evidence on both sides -> conflict category.
        insert_signal(conn, "CON", classification="neutral_institutional_activity",
                      dpss=45, confidence=0.0,
                      supporting=[item(1, 2, "A")], contradicting=[item(-1, 2, "B")])

        # HIST: old untested zone near today's price + stale old signal.
        insert_zone(conn, "HIST", as_of=date(2026, 8, 1), wavg=101.0, strength=70.0,
                    status="untested", unique_days=3, notional=5_000_000)
        insert_signal(conn, "HIST", as_of=date(2026, 7, 27),
                      classification="probable_accumulation", dpss=60)
        insert_close(conn, "HIST", 100.0)

        # INV: yesterday's signal whose invalidation level broke today.
        insert_signal(conn, "INV", as_of=date(2026, 8, 4),
                      classification="probable_accumulation", dpss=61,
                      invalidation=[{"type": "daily_close_below", "level": 95.0}])
        insert_close(conn, "INV", 94.0)
    return engine


def test_scanner_categories(engine):
    with engine.connect() as conn:
        result = scan(conn, AS_OF, SETTINGS)
    categories = result["categories"]

    fresh = [row["ticker"] for row in categories["fresh_institutional_activity"]]
    assert fresh == ["ACC", "DST", "CON"]  # DPSS-ranked, min 40
    assert "DPSS 72" in categories["fresh_institutional_activity"][0]["why"]

    assert [r["ticker"] for r in categories["repeated_accumulation_zones"]] == ["ACC"]
    assert [r["ticker"] for r in categories["repeated_distribution_zones"]] == ["DST"]

    assert [r["ticker"] for r in categories["zone_rejections"]] == ["ACC"]
    assert categories["zone_reclaims"] == []

    singles = categories["unusual_single_prints"]
    assert singles[0]["ticker"] == "ACC" and singles[0]["size_class"] == "extreme"

    assert categories["options_confirmed"] == []  # waits for evidence group D
    assert [r["ticker"] for r in categories["price_conflict"]] == ["CON"]

    levels = categories["levels_likely_to_matter"]
    assert [r["ticker"] for r in levels] == ["ACC"]
    assert levels[0]["distance_atr"] == 0.5  # |100 - 99| / ATR 2

    approaching = categories["approaching_historical_levels"]
    assert [r["ticker"] for r in approaching] == ["HIST"]
    assert approaching[0]["gap_pct"] == 1.0


def test_alert_rules_fire_once_then_cool_down(engine):
    with engine.begin() as conn:
        emitted = evaluate_alerts(conn, AS_OF, SETTINGS, now=NOW)
    rules = {(alert["rule"], alert["ticker"]) for alert in emitted}
    assert ("extreme_print", "ACC") in rules
    assert ("repeated_prints_zone", "ACC") in rules
    assert ("zone_notional_threshold", "ACC") in rules
    assert ("zone_broken", "DST") in rules
    assert ("directional_signal", "ACC") in rules
    assert ("directional_signal", "DST") in rules
    assert ("signal_invalidated", "INV") in rules
    assert ("stale_signal", "HIST") in rules
    assert not any(ticker == "CON" for _, ticker in rules)  # neutral: no alert

    with engine.begin() as conn:
        again = evaluate_alerts(conn, AS_OF, SETTINGS, now=NOW)
    assert again == []  # cooldown: everything already alerted today

    with engine.connect() as conn:
        stored = conn.execute(sa.select(sa.func.count()).select_from(alerts_table)).scalar()
    assert stored == len(emitted)


def test_per_symbol_daily_cap(engine):
    tight = Settings.model_validate({"alerts": {"max_alerts_per_symbol_per_day": 2}})
    with engine.begin() as conn:
        emitted = evaluate_alerts(conn, AS_OF, tight, now=NOW)
    acc_alerts = [alert for alert in emitted if alert["ticker"] == "ACC"]
    assert len(acc_alerts) == 2


def test_digest_rendering_and_send_guard(engine):
    with engine.begin() as conn:
        emitted = evaluate_alerts(conn, AS_OF, SETTINGS, now=NOW)
    subject, body = build_digest(AS_OF, emitted)
    assert "2026-08-05" in subject
    assert "ACC" in body and "Signals invalidated" in body
    assert "probabilities, not promises" in body.lower()

    unconfigured = Secrets(uw_api_token="x", _env_file=None)
    assert send_digest(unconfigured, subject, body) == {
        "sent": False, "reason": "smtp_not_configured"
    }


def test_digest_sends_via_injected_smtp():
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port):
            self.host, self.port = host, port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            pass

        def login(self, user, password):
            self.credentials = (user, password)

        def send_message(self, message):
            sent_messages.append(message)

    secrets = Secrets(
        uw_api_token="x", smtp_host="mail.example.com", smtp_user="u",
        smtp_password="p", alert_email_from="engine@example.com",
        alert_email_to="me@example.com", _env_file=None,
    )
    result = send_digest(secrets, "subject", "body\n", smtp_factory=FakeSMTP)
    assert result == {"sent": True, "to": "me@example.com"}
    assert sent_messages[0]["Subject"] == "subject"
    assert sent_messages[0]["To"] == "me@example.com"


def test_scan_alerts_and_report_endpoints(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_settings] = lambda: SETTINGS
    try:
        client = TestClient(app)
        with engine.begin() as conn:
            evaluate_alerts(conn, AS_OF, SETTINGS, now=NOW)

        scan_body = client.get("/scan").json()  # defaults to latest signal date
        assert scan_body["date"] == "2026-08-05"
        assert scan_body["categories"]["fresh_institutional_activity"]

        alerts_body = client.get("/alerts", params={"date": "2026-08-05"}).json()
        assert alerts_body["count"] > 0
        assert {"rule", "ticker", "payload"} <= set(alerts_body["alerts"][0])

        report = client.get("/report/acc").json()
        assert report["ticker"] == "ACC"
        assert report["verdict"] in (
            "watch", "high-priority watch", "actionable only after confirmation"
        )
        assert client.get("/report/NOPE").status_code == 404
    finally:
        app.dependency_overrides.clear()
