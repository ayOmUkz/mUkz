/** Plain-language definitions for every technical term in the UI
 * (docs/PLAN.md §15: "plain-language tooltips for every technical term").
 */

export const GLOSSARY: Record<string, string> = {
  "dark pool":
    "A private trading venue. Big trades happen there quietly and only " +
    "appear on the public tape after the fact.",
  print:
    "One reported trade. A 'dark-pool print' is a trade that happened " +
    "off-exchange and was reported afterwards.",
  dpss:
    "Dark Pool Significance Score (0-100): how much this activity matters, " +
    "combining print size, zone strength, direction confidence and " +
    "relevance - all multiplied by data quality.",
  nbbo:
    "National Best Bid and Offer - the best public buy and sell prices at " +
    "that moment. Think of it as the sticker-price range.",
  vwap:
    "Volume-Weighted Average Price - the day's average price weighted by " +
    "how much traded at each level. Institutions often benchmark to it.",
  atr:
    "Average True Range - how much the stock typically moves in a day. " +
    "Used to scale levels so a $12 and a $1,200 stock are comparable.",
  zone:
    "A price area where many large dark-pool prints cluster - a 'watering " +
    "hole' institutions keep returning to.",
  accumulation:
    "Evidence suggests someone has been building a position. Always " +
    "probabilistic - the tape never says who initiated a trade.",
  distribution:
    "Evidence suggests someone has been unloading a position. Always " +
    "probabilistic - the tape never says who initiated a trade.",
  confidence:
    "How strongly the evidence leans one way (capped at 0.85 - this " +
    "system is never certain, by design).",
  invalidation:
    "The price level or condition that would prove the current reading " +
    "wrong. Every directional call ships with one.",
  "adv":
    "Average Daily Volume over the last 30 days. A print worth 1%+ of ADV " +
    "is exceptional for that stock.",
  premium:
    "The dollar value of a trade: price x shares. 'How big was the check.'",
  "size class":
    "How unusual a print's size is versus that symbol's own history: " +
    "normal, elevated (top 10%), unusual (top 1%), extreme (top 0.1%).",
  character:
    "Best-effort read of what kind of trade this was (VWAP fill, " +
    "negotiated block, derivative-linked...). Always 'probable', never " +
    "certain.",
  "location":
    "Where the trade executed relative to the public quote: at the bid, " +
    "midpoint, ask, or outside. A feature, never a verdict.",
  "late report":
    "The print hit the tape well after it executed - often a negotiated " +
    "block. Its quote-based stats are treated with less trust.",
  respected:
    "Price came back to the zone and bounced away from it - the level " +
    "acted as support or resistance.",
  broken:
    "Price closed decisively through the zone. If it stays broken, the " +
    "level failed.",
  reclaimed:
    "The zone broke, but price closed back across it within a few " +
    "sessions - often a strong signal.",
  untested: "Price has not returned to this zone since the prints happened.",
  verdict:
    "The bottom line: watch, high-priority watch, actionable only after " +
    "confirmation, avoid, or insufficient evidence. Never a guarantee.",
  "data quality":
    "How trustworthy today's inputs are (0-100). It multiplies the DPSS, " +
    "so bad data can only lower a score.",
};

export function define(term: string): string | undefined {
  return GLOSSARY[term.toLowerCase()];
}
