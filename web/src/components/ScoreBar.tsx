import { Term } from "@/components/Term";

/** One labeled 0-100 score with a visible bar — "show your work". */
export function ScoreBar({
  label,
  term,
  value,
}: {
  label: string;
  term?: string;
  value: number;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="scorebar">
      <span className="scorebar-label">
        {term ? <Term k={term}>{label}</Term> : label}
      </span>
      <div className="scorebar-track">
        <div className="scorebar-fill" style={{ width: `${clamped}%` }} />
      </div>
      <span className="scorebar-value">{value.toFixed(1)}</span>
    </div>
  );
}
