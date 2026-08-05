/** Typed fetch helpers for the FastAPI backend.
 *
 * The dashboard only ever talks to our own backend — the Unusual Whales
 * token never reaches the browser (docs/PLAN.md §18).
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) {
    throw new Error(`${path} -> HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export interface ScanRow {
  ticker: string;
  why: string;
  dpss?: number;
  classification?: string;
  confidence?: number;
  zone?: number;
  strength?: number;
  distance_atr?: number;
  gap_pct?: number;
  size?: number;
  premium?: number;
  size_class?: string;
  session?: string;
  from_date?: string;
}

export interface ScanResult {
  date: string;
  market: { spy_trend: string | null; qqq_trend: string | null };
  categories: Record<string, ScanRow[]>;
}

export interface Alert {
  rule: string;
  ticker: string;
  as_of: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Status {
  last_run: {
    date: string;
    started_at: string;
    finished_at: string | null;
    stats: { totals?: Record<string, number> } | null;
  } | null;
  latest_signal_date: string | null;
  counts: Record<string, number>;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface Zone {
  low: number;
  high: number;
  wavg: number;
  strength_score: number;
  strength_class: string;
  status: string;
  unique_days: number;
  total_shares: number;
}

export interface SymbolPrint {
  executed_at: string;
  session: string;
  price: number;
  size: number;
  size_class: string | null;
  size_percentile: number | null;
  premium: number;
}

export interface SymbolDetail {
  ticker: string;
  date: string;
  candles: Candle[];
  vwap: number | null;
  atr: number | null;
  zones: Zone[];
  prints: SymbolPrint[];
  invalidation: { type: string; level?: number; description?: string }[];
  signal: {
    classification: string;
    confidence: number;
    dpss: number;
  } | null;
}

export interface Report {
  ticker: string;
  as_of: string;
  current_price: number | null;
  market_regime: { spy_trend: string | null; qqq_trend: string | null };
  sector: string | null;
  sector_trend: string | null;
  context: { labels: string[]; conflicts: string[]; summary: string };
  summary: {
    relevant_prints: number;
    total_shares: number;
    total_notional: number;
    main_zone: {
      wavg_price: number;
      low: number;
      high: number;
      strength_score: number;
      strength_class: string;
      status: string;
    } | null;
    distance_from_price_pct: number | null;
    pct_of_adv30: number | null;
    freshness_sessions: number | null;
    data_quality_score: number;
  };
  interpretation: {
    classification: string;
    confidence: number;
    bullish_evidence: string[];
    bearish_evidence: string[];
    contradictory_evidence: string[];
    most_likely: string;
    alternative: string;
  };
  levels: Record<string, number | null>;
  scenarios: { bullish: string; neutral: string; bearish: string };
  scores: Record<string, number | Record<string, number>>;
  dpss: number;
  verdict: string;
}

export interface TapePrint {
  executed_at: string;
  created_at: string;
  report_delay_s: number;
  ticker: string;
  price: number;
  size: number;
  premium: number;
  sale_cond_codes: string | null;
  trade_code: string | null;
  nbbo_bid: number | null;
  nbbo_ask: number | null;
  mid: number | null;
  location_bucket: string | null;
  location_confidence: string;
  vwap_position: string | null;
  timing_bucket: string | null;
  size_class: string | null;
  size_percentile: number | null;
  size_confidence: string | null;
  character: string | null;
  quality_flags: string[];
}

export interface Tape {
  ticker: string;
  count: number;
  prints: TapePrint[];
}
