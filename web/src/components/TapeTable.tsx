import type { TapePrint } from "@/lib/api";
import { Term } from "@/components/Term";

const CLASS_BADGE: Record<string, string> = {
  extreme: "badge badge-red",
  unusual: "badge badge-amber",
  elevated: "badge badge-blue",
  normal: "badge",
};

function timeOf(iso: string): string {
  return new Date(iso).toISOString().slice(11, 19) + "Z";
}

/** The dark-pool tape (docs/PLAN.md §15): one row per validated print. */
export function TapeTable({ prints }: { prints: TapePrint[] }) {
  if (prints.length === 0) {
    return <p className="muted">No prints stored for this selection.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>
              <Term k="print">Executed</Term>
            </th>
            <th>Reported</th>
            <th>Price</th>
            <th>Size</th>
            <th>
              <Term k="premium">Premium</Term>
            </th>
            <th>
              <Term k="nbbo">Bid / Ask</Term>
            </th>
            <th>
              <Term k="location">Location</Term>
            </th>
            <th>
              <Term k="size class">Class</Term>
            </th>
            <th>Timing</th>
            <th>
              <Term k="character">Character</Term>
            </th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {prints.map((print) => (
            <tr key={`${print.ticker}-${print.executed_at}-${print.size}`}>
              <td>{timeOf(print.executed_at)}</td>
              <td>
                {timeOf(print.created_at)}
                {print.report_delay_s > 900 ? (
                  <Term k="late report">
                    <span className="badge badge-amber">late</span>
                  </Term>
                ) : null}
              </td>
              <td>{print.price.toFixed(2)}</td>
              <td>{print.size.toLocaleString()}</td>
              <td>${(print.premium / 1e6).toFixed(2)}M</td>
              <td>
                {print.nbbo_bid !== null && print.nbbo_ask !== null
                  ? `${print.nbbo_bid.toFixed(2)} / ${print.nbbo_ask.toFixed(2)}`
                  : "n/a"}
              </td>
              <td>{print.location_bucket ?? "n/a"}</td>
              <td>
                <span className={CLASS_BADGE[print.size_class ?? "normal"]}>
                  {print.size_class ?? "?"}
                </span>
              </td>
              <td>{print.timing_bucket ?? "?"}</td>
              <td>{print.character ?? "?"}</td>
              <td className="muted">
                {print.quality_flags.length > 0 ? print.quality_flags.join(", ") : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
