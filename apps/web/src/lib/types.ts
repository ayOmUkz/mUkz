// TS mirror of the Python schemas in apps/quant/app/schemas.py.
// V2 cleanup: auto-generate from FastAPI OpenAPI.

export type Sign = "+" | "-";

export type OptionType = "call" | "put";
export type Side = "long" | "short";

export interface Position {
  ticker: string;
  expiration: string; // ISO date YYYY-MM-DD
  strike: number;
  option_type: OptionType;
  side: Side;
  qty: number;
  entry_price?: number | null;
}

export interface ChainContext {
  underlying_price: number;
  dte: number;
  multiplier: number;
  bid: number;
  ask: number;
  mid: number;
  iv: number;
  iv_rank: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  open_interest: number;
  volume: number;
}

export interface EnrichedPosition {
  position: Position;
  context: ChainContext;
}

export interface ClassifyResponse {
  scores: ForceScores;
  classification: Classification;
}

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
