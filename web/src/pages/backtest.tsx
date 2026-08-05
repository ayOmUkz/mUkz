import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { Term } from "@/components/Term";

interface BacktestMetrics {
  n: number;
  hit_rate: number;
  mean_return: number;
  median_return: number;
  ci_low: number;
  ci_high: number;
  mean_market_adj: number | null;
  mean_mfe: number;
  mean_mae: number;
  false_positive_rate: number;
  thin_sample: boolean;
}

interface BacktestRun {
  run_id: number;
  created_at: string;
  config_hash: string;
  summary: {
    events_total: number;
    events_headline: number;
    events_overlapping: number;
    events_unmeasurable: number;
    no_edge_cohorts: string[];
    notes: string[];
  };
  results: { cohort: string; horizon: number; metrics: BacktestMetrics }[];
}

const pct = (value: number | null) =>
  value !== null ? `${(value * 100).toFixed(2)}%` : "n/a";

export default function BacktestPage() {
  const [run, setRun] = useState<BacktestRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJson<BacktestRun>("/backtest").then(setRun).catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <p className="muted">
        No backtest run stored yet — run <code>python -m app.jobs.backtest</code>{" "}
        once signals have accumulated. ({error})
      </p>
    );
  }
  if (!run) {
    return <p className="muted">Loading…</p>;
  }
  return (
    <>
      <div className="banner">
        <span>
          Run #{run.run_id} · config <code>{run.config_hash}</code> ·{" "}
          {run.summary.events_headline} headline events (
          {run.summary.events_overlapping} overlapping excluded,{" "}
          {run.summary.events_unmeasurable} unmeasurable)
        </span>
      </div>

      <section className="card">
        <h3>Cohorts</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Cohort</th>
                <th>Horizon</th>
                <th>n</th>
                <th>Hit rate</th>
                <th>Mean</th>
                <th>95% CI</th>
                <th>Mkt-adj</th>
                <th>MFE</th>
                <th>MAE</th>
                <th>
                  <Term k="invalidation">FP rate</Term>
                </th>
              </tr>
            </thead>
            <tbody>
              {run.results.map((row) => (
                <tr key={`${row.cohort}-${row.horizon}`}>
                  <td>
                    {row.cohort}
                    {row.metrics.thin_sample ? (
                      <span className="badge badge-amber">thin</span>
                    ) : null}
                  </td>
                  <td>{row.horizon}d</td>
                  <td>{row.metrics.n}</td>
                  <td>{(row.metrics.hit_rate * 100).toFixed(0)}%</td>
                  <td>{pct(row.metrics.mean_return)}</td>
                  <td>
                    [{pct(row.metrics.ci_low)}, {pct(row.metrics.ci_high)}]
                  </td>
                  <td>{pct(row.metrics.mean_market_adj)}</td>
                  <td>{pct(row.metrics.mean_mfe)}</td>
                  <td>{pct(row.metrics.mean_mae)}</td>
                  <td>{(row.metrics.false_positive_rate * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h3>No demonstrated edge</h3>
        {run.summary.no_edge_cohorts.length > 0 ? (
          <>
            <p className="small">
              Enough data to judge, and the confidence interval does not
              exclude zero — treat these as unproven:
            </p>
            <ul>
              {run.summary.no_edge_cohorts.map((name) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          </>
        ) : (
          <p className="muted">
            No cohort met the sample-size bar for a null verdict yet — a
            statement about sample size, not about edge.
          </p>
        )}
      </section>

      <section className="card">
        <h3>Disclosures</h3>
        <ul className="small">
          {run.summary.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>
    </>
  );
}
