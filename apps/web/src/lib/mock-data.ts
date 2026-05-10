// Hardcoded sample for offline / Python-service-down fallback.
// SAMPLE_POSITION is also the payload sent to /classify for the V1 demo.

import type {
  Classification,
  EnrichedPosition,
  ForceScores,
} from "./types";

export const SAMPLE_POSITION: EnrichedPosition = {
  position: {
    ticker: "SPY",
    expiration: "2025-12-19",
    strike: 480.0,
    option_type: "call",
    side: "long",
    qty: 5,
    entry_price: 8.5,
  },
  context: {
    underlying_price: 480.0,
    dte: 30,
    multiplier: 100,
    bid: 8.4,
    ask: 8.6,
    mid: 8.5,
    iv: 0.25,
    iv_rank: 50,
    delta: 0.5,
    gamma: 0.03,
    theta: -0.15,
    vega: 0.4,
    open_interest: 10000,
    volume: 5000,
  },
};

export const MOCK_FORCE_SCORES: ForceScores = {
  delta: { magnitude: 1.0, sign: "+" },
  gamma: { magnitude: 7.2, sign: "+" },
  theta: { magnitude: 2.0, sign: "-" },
  vega: { magnitude: 1.8, sign: "+" },
  premium_fairness: { magnitude: 5.1, sign: null },
};

export const MOCK_CLASSIFICATION: Classification = {
  primary: "Convexity Trade",
  qualifier: "Long Gamma Scalp",
  confidence: 0.62,
  dominant_axis: "gamma",
  secondary_axis: "theta",
  readout:
    "1x SPY 2025-12-19 480C, long. Long Gamma Scalp Convexity Trade. You're bullish on direction, long vol on IV, and paying theta day to day.",
};
