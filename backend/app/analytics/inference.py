"""Accumulation vs distribution: the evidence ledger (plan §10).

*Analogy: a court case. One witness — however loud — never convicts. You
need independent witnesses telling a consistent story, and the defense
(contradicting evidence) is always heard.*

Evidence items carry a direction (+1 leans accumulation, −1 leans
distribution), a weight (1–3) and a source group; verdicts require both
enough net weight AND evidence from independent groups:

* **A** — dark-pool structure (the prints themselves),
* **B** — price behavior around the zone,
* **C** — volume asymmetry (a CVD *proxy* from daily bars — the API has no
  tick-level CVD),
* **D** — options confirmation (wired in M4 with market context; no items
  are generated yet).

Confidence is a squash of net weight, hard-capped below certainty.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from app.config import InferenceConfig

#: Ratio of up-day to down-day volume that counts as asymmetric.
VOLUME_ASYMMETRY_RATIO = 1.3
#: Call/put premium ratio that counts as an options tilt (group D).
OPTIONS_TILT_RATIO = 1.5
#: Net-weight scale of the confidence squash (tanh(net / SCALE) * cap).
CONFIDENCE_SCALE = 6.0


@dataclass
class Evidence:
    id: str
    group: str  # A | B | C | D
    direction: int  # +1 accumulation-leaning, -1 distribution-leaning
    weight: int  # 1..3
    description: str


def build_evidence(
    zone: dict[str, Any],
    status: dict[str, Any],
    daily: list[dict[str, Any]],
    *,
    current_close: float | None,
    options_tilt: dict[str, Any] | None = None,
) -> list[Evidence]:
    """Generate ledger items from one zone + its price context."""
    items: list[Evidence] = []
    wavg = float(zone["wavg_price"])

    # --- Group A: dark-pool structure -----------------------------------
    tight = zone.get("tightness_atr")
    if zone["unique_days"] >= 3 and (tight is None or tight <= 1.0):
        if current_close is not None and current_close >= wavg:
            items.append(
                Evidence(
                    "A_repeat_holding",
                    "A",
                    +1,
                    2,
                    f"prints on {zone['unique_days']} sessions in a tight zone "
                    f"while price holds at/above {wavg:.2f}",
                )
            )
        elif current_close is not None:
            items.append(
                Evidence(
                    "A_repeat_failing",
                    "A",
                    -1,
                    2,
                    f"prints on {zone['unique_days']} sessions in a tight zone "
                    f"while price sits below {wavg:.2f}",
                )
            )

    # --- Group B: price behavior around the zone ------------------------
    respected = status.get("respected_touches", 0)
    if status.get("status") in ("respected", "reclaimed") and respected:
        # A bounce back above the zone means it acted as support (bullish);
        # break_to tells us which side a broken zone failed toward.
        items.append(
            Evidence(
                "B_respected",
                "B",
                +1 if (current_close or wavg) >= wavg else -1,
                2,
                f"zone respected {respected}x by closing price reactions",
            )
        )
    if status.get("status") == "broken":
        direction = -1 if status.get("break_to") == "below" else +1
        side = "down through" if direction < 0 else "up through"
        items.append(
            Evidence("B_broken", "B", direction, 2, f"price closed {side} the zone")
        )
    if status.get("status") == "reclaimed":
        direction = +1 if status.get("break_to") == "below" else -1
        items.append(
            Evidence("B_reclaimed", "B", direction, 2, "zone was broken, then reclaimed")
        )

    bars = sorted(daily, key=lambda b: b["ts"])
    if len(bars) >= 4:
        lows = [float(bar["low"]) for bar in bars[-4:]]
        highs = [float(bar["high"]) for bar in bars[-4:]]
        if all(a < b for a, b in zip(lows, lows[1:], strict=False)):
            items.append(Evidence("B_higher_lows", "B", +1, 1, "higher lows, last 4 sessions"))
        if all(a > b for a, b in zip(highs, highs[1:], strict=False)):
            items.append(Evidence("B_lower_highs", "B", -1, 1, "lower highs, last 4 sessions"))

    # --- Group C: volume asymmetry (CVD proxy) --------------------------
    up_volume = down_volume = 0
    for previous, current in zip(bars[:-1], bars[1:], strict=False):
        volume = current.get("volume") or 0
        if current["close"] > previous["close"]:
            up_volume += volume
        elif current["close"] < previous["close"]:
            down_volume += volume
    if up_volume and down_volume:
        ratio = up_volume / down_volume
        if ratio >= VOLUME_ASYMMETRY_RATIO:
            items.append(
                Evidence(
                    "C_up_volume", "C", +1, 1,
                    f"up-day volume {ratio:.2f}x down-day volume (CVD proxy)",
                )
            )
        elif ratio <= 1 / VOLUME_ASYMMETRY_RATIO:
            items.append(
                Evidence(
                    "C_down_volume", "C", -1, 1,
                    f"down-day volume {1 / ratio:.2f}x up-day volume (CVD proxy)",
                )
            )

    # --- Group D: options confirmation (daily premium tilt) --------------
    if options_tilt:
        call = float(options_tilt.get("call_premium") or 0)
        put = float(options_tilt.get("put_premium") or 0)
        if call > 0 and put > 0:
            tilt = call / put
            if tilt >= OPTIONS_TILT_RATIO:
                items.append(
                    Evidence(
                        "D_call_tilt", "D", +1, 1,
                        f"options premium tilted to calls ({tilt:.1f}x puts)",
                    )
                )
            elif tilt <= 1 / OPTIONS_TILT_RATIO:
                items.append(
                    Evidence(
                        "D_put_tilt", "D", -1, 1,
                        f"options premium tilted to puts ({1 / tilt:.1f}x calls)",
                    )
                )
    return items


def infer(evidence: list[Evidence], config: InferenceConfig) -> dict[str, Any]:
    """Turn ledger items into one of the six verdict states (plan §10)."""
    supporting = [item for item in evidence if item.direction > 0]
    contradicting = [item for item in evidence if item.direction < 0]
    net = sum(item.direction * item.weight for item in evidence)
    groups = {item.group for item in evidence}
    leaning = "accumulation" if net > 0 else "distribution"
    # The verdict's own evidence is whichever side the net leans toward.
    aligned = supporting if net > 0 else contradicting

    if len(evidence) < config.possible_min_items or len(groups) < 2:
        classification = "insufficient_evidence"
    elif (
        abs(net) >= config.probable_net_weight
        and len(aligned) >= config.probable_min_items
        and len(groups) >= config.min_source_groups
    ):
        classification = f"probable_{leaning}"
    elif abs(net) >= config.possible_net_weight and len(aligned) >= config.possible_min_items:
        classification = f"possible_{leaning}"
    else:
        classification = "neutral_institutional_activity"

    confidence = 0.0
    if classification.startswith(("probable", "possible")):
        confidence = round(config.confidence_cap * math.tanh(abs(net) / CONFIDENCE_SCALE), 2)

    return {
        "classification": classification,
        "confidence": confidence,
        "net_weight": net,
        "groups": sorted(groups),
        "supporting": [asdict(item) for item in supporting],
        "contradicting": [asdict(item) for item in contradicting],
    }


def invalidation_conditions(
    zone: dict[str, Any], classification: str, *, atr: float | None
) -> list[dict[str, Any]]:
    """Machine-generated 'what would kill this signal' (plan §10)."""
    if not classification.startswith(("probable", "possible")):
        return []
    atr_value = atr if atr and atr > 0 else float(zone["wavg_price"]) * 0.01
    if classification.endswith("accumulation"):
        level = float(zone["price_low"]) - 0.5 * atr_value
        conditions = [
            {
                "type": "daily_close_below",
                "level": round(level, 4),
                "description": f"daily close below {level:.2f} (zone low − 0.5×ATR)",
            }
        ]
    else:
        level = float(zone["price_high"]) + 0.5 * atr_value
        conditions = [
            {
                "type": "daily_close_above",
                "level": round(level, 4),
                "description": f"daily close above {level:.2f} (zone high + 0.5×ATR)",
            }
        ]
    conditions.append(
        {
            "type": "zone_broken_unreclaimed",
            "sessions": 3,
            "description": "zone broken and not reclaimed within 3 sessions",
        }
    )
    return conditions
