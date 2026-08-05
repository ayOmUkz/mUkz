import Link from "next/link";
import { useEffect, useState } from "react";
import type { Alert, ScanResult, ScanRow, Status } from "@/lib/api";
import { fetchJson } from "@/lib/api";
import { LiveFeed } from "@/components/LiveFeed";
import { Term } from "@/components/Term";

function CategoryCard({
  title,
  term,
  rows,
  empty,
}: {
  title: string;
  term?: string;
  rows: ScanRow[];
  empty: string;
}) {
  return (
    <section className="card">
      <h3>{term ? <Term k={term}>{title}</Term> : title}</h3>
      {rows.length === 0 ? (
        <p className="muted">{empty}</p>
      ) : (
        <ul className="scan-list">
          {rows.map((row) => (
            <li key={`${row.ticker}-${row.why}`}>
              <Link href={`/symbol/${row.ticker}`} className="ticker">
                {row.ticker}
              </Link>
              {row.dpss !== undefined ? (
                <span className="badge badge-blue">
                  <Term k="dpss">DPSS {row.dpss.toFixed(0)}</Term>
                </span>
              ) : null}
              <span className="why">{row.why}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function Overview() {
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJson<ScanResult>("/scan").then(setScan).catch((e) => setError(String(e)));
    fetchJson<{ alerts: Alert[] }>("/alerts?limit=25")
      .then((body) => setAlerts(body.alerts))
      .catch(() => undefined);
    fetchJson<Status>("/status").then(setStatus).catch(() => undefined);
  }, []);

  if (error) {
    return (
      <p className="muted">
        Could not reach the backend ({error}). Is the API running on port 8000
        and has a nightly run completed?
      </p>
    );
  }
  if (!scan) {
    return <p className="muted">Loading…</p>;
  }
  const categories = scan.categories;
  const totals = status?.last_run?.stats?.totals;
  return (
    <>
      <div className="banner">
        <span>
          Session <strong>{scan.date}</strong> · SPY{" "}
          {scan.market.spy_trend ?? "n/a"} · QQQ {scan.market.qqq_trend ?? "n/a"}
        </span>
        {status ? (
          <span>
            <Term k="data quality">Data</Term>: {totals?.clean ?? "?"} clean /{" "}
            {totals?.rejected ?? "?"} quarantined ·{" "}
            {status.counts.signals} signals · {status.counts.zones} zones
          </span>
        ) : null}
      </div>

      <div className="grid">
        <CategoryCard
          title="Strongest institutional activity"
          term="dark pool"
          rows={categories.fresh_institutional_activity ?? []}
          empty="Nothing above the significance floor today."
        />
        <CategoryCard
          title="Top accumulation candidates"
          term="accumulation"
          rows={categories.repeated_accumulation_zones ?? []}
          empty="No repeated accumulation zones today — no candidate is forced."
        />
        <CategoryCard
          title="Top distribution candidates"
          term="distribution"
          rows={categories.repeated_distribution_zones ?? []}
          empty="No repeated distribution zones today."
        />
        <CategoryCard
          title="Levels likely to matter today"
          term="zone"
          rows={categories.levels_likely_to_matter ?? []}
          empty="No strong zone sits within one ATR of price."
        />
        <CategoryCard
          title="Unusually large single prints"
          term="size class"
          rows={categories.unusual_single_prints ?? []}
          empty="No unusual or extreme prints today."
        />
        <CategoryCard
          title="Conflicting signals"
          term="invalidation"
          rows={categories.price_conflict ?? []}
          empty="No symbol has meaningful evidence on both sides."
        />
        <CategoryCard
          title="Reclaims / rejections"
          term="reclaimed"
          rows={[
            ...(categories.zone_reclaims ?? []),
            ...(categories.zone_rejections ?? []),
          ]}
          empty="No strong zone was reclaimed or rejected recently."
        />
        <CategoryCard
          title="Historical levels approaching"
          term="untested"
          rows={categories.approaching_historical_levels ?? []}
          empty="No untested historical zone is near current price."
        />
      </div>

      <LiveFeed />

      <section className="card">
        <h3>Alerts</h3>
        {alerts.length === 0 ? (
          <p className="muted">No alerts. Quiet tape, quiet feed.</p>
        ) : (
          <ul className="alert-list">
            {alerts.map((alert) => (
              <li key={`${alert.rule}-${alert.ticker}-${alert.created_at}`}>
                <span className="badge">{alert.rule}</span>
                <Link href={`/symbol/${alert.ticker}`} className="ticker">
                  {alert.ticker}
                </Link>
                <span className="why">
                  {Object.entries(alert.payload)
                    .slice(0, 4)
                    .map(([key, value]) => `${key}=${String(value)}`)
                    .join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
