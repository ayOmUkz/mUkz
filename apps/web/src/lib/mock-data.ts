// Hardcoded sample matching the Python classifier output for an ATM long call.
// Replaces real fetch in the vertical slice; wire /classify in the next iteration.

import type { Classification, ForceScores } from "./types";

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
