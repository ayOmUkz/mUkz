import { Term } from "@/components/Term";

/** Bullish, bearish, and contradictory evidence side by side.
 * Honesty is a feature: the column that disagrees is always shown.
 */
export function EvidencePanel({
  bullish,
  bearish,
  contradictory,
}: {
  bullish: string[];
  bearish: string[];
  contradictory: string[];
}) {
  const column = (title: string, term: string, items: string[]) => (
    <div className="evidence-col">
      <h4>
        <Term k={term}>{title}</Term>
      </h4>
      {items.length === 0 ? (
        <p className="muted">none</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
  return (
    <div className="evidence">
      {column("Bullish evidence", "accumulation", bullish)}
      {column("Bearish evidence", "distribution", bearish)}
      {column("Contradictory", "invalidation", contradictory)}
    </div>
  );
}
