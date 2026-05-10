from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

OptionType = Literal["call", "put"]
Side = Literal["long", "short"]
Sign = Literal["+", "-"]
AxisName = Literal["delta", "gamma", "theta", "vega", "premium_fairness"]
PrimaryLabel = Literal[
    "Directional Bet",
    "Theta Harvest",
    "Volatility Play",
    "Convexity Trade",
    "Decay Trap",
    "Mixed Exposure",
]


class Position(BaseModel):
    """A single options leg as the user enters it. V1 Path A: single-leg only."""

    ticker: str
    expiration: date
    strike: float
    option_type: OptionType
    side: Side
    qty: int = Field(ge=1)
    entry_price: float | None = None


class ChainContext(BaseModel):
    """Market context for a contract at the moment of classification."""

    underlying_price: float
    dte: int = Field(ge=0)
    multiplier: int = 100
    bid: float
    ask: float
    mid: float
    iv: float = Field(description="implied volatility as a decimal, e.g. 0.25 = 25%")
    iv_rank: float = Field(ge=0, le=100, description="IV rank percentile 0-100")
    delta: float
    gamma: float
    theta: float = Field(description="per-day theta (vendor convention)")
    vega: float
    open_interest: int = 0
    volume: int = 0


class EnrichedPosition(BaseModel):
    """Position + ChainContext together; what the scorer consumes."""

    position: Position
    context: ChainContext


class ForceScore(BaseModel):
    magnitude: float = Field(ge=0, le=10)
    sign: Sign | None = None  # premium_fairness is unsigned


class ForceScores(BaseModel):
    delta: ForceScore
    gamma: ForceScore
    theta: ForceScore
    vega: ForceScore
    premium_fairness: ForceScore

    def by_axis(self) -> dict[AxisName, ForceScore]:
        return {
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
            "premium_fairness": self.premium_fairness,
        }


class Classification(BaseModel):
    primary: PrimaryLabel
    qualifier: str | None = None
    confidence: float = Field(ge=0, le=1)
    dominant_axis: AxisName | None = None
    secondary_axis: AxisName | None = None
    readout: str = Field(description="plain-English summary of the position's exposure")
