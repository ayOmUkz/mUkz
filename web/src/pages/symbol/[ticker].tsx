import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";
import type { Report, SymbolDetail, Tape } from "@/lib/api";
import { fetchJson } from "@/lib/api";
import { EvidencePanel } from "@/components/EvidencePanel";
import { PriceChart } from "@/components/PriceChart";
import { ScoreBar } from "@/components/ScoreBar";
import { TapeTable } from "@/components/TapeTable";
import { Term } from "@/components/Term";

const VERDICT_BADGE: Record<string, string> = {
  "high-priority watch": "badge badge-red",
  watch: "badge badge-amber",
  "actionable only after confirmation": "badge badge-blue",
  avoid: "badge",
  "insufficient evidence": "badge",
};

export default function SymbolPage() {
  const router = useRouter();
  const ticker = typeof router.query.ticker === "string" ? router.query.ticker : null;

  const [detail, setDetail] = useState<SymbolDetail | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [tape, setTape] = useState<Tape | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) {
      return;
    }
    fetchJson<SymbolDetail>(`/symbol/${ticker}`)
      .then(setDetail)
      .catch((e) => setError(String(e)));
    fetchJson<Report>(`/report/${ticker}`)
      .then(setReport)
      .catch(() => setReport(null)); // chart + tape still render without a signal
    fetchJson<Tape>(`/tape?ticker=${ticker}`).then(setTape).catch(() => undefined);
  }, [ticker]);

  const invalidationLevels = useMemo(
    () =>
      (detail?.invalidation ?? [])
        .map((condition) => condition.level)
        .filter((level): level is number => typeof level === "number"),
    [detail],
  );

  if (error) {
    return <p className="muted">Nothing stored for this symbol yet ({error}).</p>;
  }
  if (!detail) {
    return <p className="muted">Loading…</p>;
  }

  const scores = report?.scores as Record<string, number> | undefined;
  return (
    <>
      <div className="symbol-head">
        <h2>{detail.ticker}</h2>
        <span className="muted">{detail.date}</span>
        {report ? (
          <span className={VERDICT_BADGE[report.verdict] ?? "badge"}>
            <Term k="verdict">{report.verdict}</Term>
          </span>
        ) : null}
        {detail.signal ? (
          <span className="muted">
            {detail.signal.classification.replaceAll("_", " ")} ·{" "}
            <Term k="confidence">conf {detail.signal.confidence.toFixed(2)}</Term> ·{" "}
            <Term k="dpss">DPSS {detail.signal.dpss.toFixed(1)}</Term>
          </span>
        ) : null}
      </div>

      <section className="card">
        <PriceChart
          candles={detail.candles}
          zones={detail.zones}
          vwap={detail.vwap}
          invalidationLevels={invalidationLevels}
          prints={detail.prints}
        />
        <p className="muted small">
          Amber lines: <Term k="zone">dark-pool zones</Term> (solid = strong) ·
          blue dashed: <Term k="vwap">VWAP</Term> · red dashed:{" "}
          <Term k="invalidation">invalidation</Term> · dots: prints sized by{" "}
          <Term k="size class">class</Term>.
        </p>
      </section>

      {report ? (
        <div className="grid">
          <section className="card">
            <h3>Score breakdown</h3>
            {scores ? (
              <>
                <ScoreBar label="Print significance" term="print" value={Number(scores.print ?? 0)} />
                <ScoreBar label="Zone significance" term="zone" value={Number(scores.zone ?? 0)} />
                <ScoreBar label="Direction confidence" term="confidence" value={Number(scores.direction ?? 0)} />
                <ScoreBar label="Trade relevance" value={Number(scores.relevance ?? 0)} />
                <ScoreBar label="Data quality (gate)" term="data quality" value={Number(scores.quality ?? 0)} />
                <ScoreBar label="DPSS" term="dpss" value={report.dpss} />
              </>
            ) : null}
          </section>
          <section className="card">
            <h3>Important levels</h3>
            <ul className="levels">
              {Object.entries(report.levels).map(([name, value]) => (
                <li key={name}>
                  <span>{name.replaceAll("_", " ")}</span>
                  <strong>{value !== null ? value.toFixed(2) : "n/a"}</strong>
                </li>
              ))}
            </ul>
            <h3>Scenario map</h3>
            <p className="small">Bullish: {report.scenarios.bullish}</p>
            <p className="small">Neutral: {report.scenarios.neutral}</p>
            <p className="small">Bearish: {report.scenarios.bearish}</p>
          </section>
        </div>
      ) : (
        <p className="muted">
          No signal stored for this session — run the nightly pipeline, or this
          symbol simply had nothing worth interpreting (which is an answer too).
        </p>
      )}

      {report ? (
        <section className="card">
          <h3>Evidence</h3>
          <EvidencePanel
            bullish={report.interpretation.bullish_evidence}
            bearish={report.interpretation.bearish_evidence}
            contradictory={report.interpretation.contradictory_evidence}
          />
          <p className="small">
            Most likely: {report.interpretation.most_likely}
          </p>
          <p className="small muted">
            Alternative: {report.interpretation.alternative}
          </p>
        </section>
      ) : null}

      <section className="card">
        <h3>
          <Term k="print">Dark-pool tape</Term>
        </h3>
        {tape ? <TapeTable prints={tape.prints} /> : <p className="muted">Loading…</p>}
      </section>
    </>
  );
}
