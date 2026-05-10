// TS mirror of the Python schemas in apps/quant/app/schemas.py.
// V2 cleanup: auto-generate from FastAPI OpenAPI.

export type Sign = "+" | "-";

export type AxisName =
  | "delta"
  | "gamma"
  | "theta"
  | "vega"
  | "premium_fairness";

export type PrimaryLabel =
  | "Directional Bet"
  | "Theta Harvest"
  | "Volatility Play"
  | "Convexity Trade"
  | "Decay Trap"
  | "Mixed Exposure";

export interface ForceScore {
  magnitude: number; // 0-10
  sign: Sign | null;
}

export interface ForceScores {
  delta: ForceScore;
  gamma: ForceScore;
  theta: ForceScore;
  vega: ForceScore;
  premium_fairness: ForceScore;
}

export interface Classification {
  primary: PrimaryLabel;
  qualifier: string | null;
  confidence: number; // 0-1
  dominant_axis: AxisName | null;
  secondary_axis: AxisName | null;
  readout: string;
}

export const AXIS_ORDER: AxisName[] = [
  "delta",
  "gamma",
  "theta",
  "vega",
  "premium_fairness",
];

export const AXIS_GLYPH: Record<AxisName, string> = {
  delta: "Δ",
  gamma: "Γ",
  theta: "Θ",
  vega: "ν",
  premium_fairness: "Fair",
};
