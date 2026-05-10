"use client";

import { useEffect, useState } from "react";

import { AddPositionDialog } from "@/components/AddPositionDialog";
import { GreekRadar } from "@/components/GreekRadar";
import { PersonalityLabel } from "@/components/PersonalityLabel";
import { PlainEnglishReadout } from "@/components/PlainEnglishReadout";
import {
  MOCK_CLASSIFICATION,
  MOCK_FORCE_SCORES,
  SAMPLE_POSITION,
} from "@/lib/mock-data";
import type {
  Classification,
  ClassifyResponse,
  EnrichedPosition,
  ForceScores,
} from "@/lib/types";

export default function Home() {
  const [position, setPosition] = useState<EnrichedPosition>(SAMPLE_POSITION);
  const [scores, setScores] = useState<ForceScores>(MOCK_FORCE_SCORES);
  const [classification, setClassification] =
    useState<Classification>(MOCK_CLASSIFICATION);
  const [dataSource, setDataSource] = useState<"Live" | "Mock" | "Loading">(
    "Loading",
  );
  const [showDialog, setShowDialog] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setDataSource("Loading");
    fetch("/api/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(position),
    })
      .then((res) => (res.ok ? (res.json() as Promise<ClassifyResponse>) : null))
      .then((data) => {
        if (cancelled) return;
        if (data) {
          setScores(data.scores);
          setClassification(data.classification);
          setDataSource("Live");
        } else {
          setDataSource("Mock");
        }
      })
      .catch(() => {
        if (!cancelled) setDataSource("Mock");
      });
    return () => {
      cancelled = true;
    };
  }, [position]);

  const sourceColor =
    dataSource === "Live"
      ? "text-emerald-400"
      : dataSource === "Loading"
        ? "text-slate-400"
        : "text-amber-400";

  return (
    <main className="flex flex-1 flex-col items-center justify-start gap-8 px-6 py-12">
      <header className="flex w-full max-w-5xl items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs uppercase tracking-[0.3em] text-slate-500">
            Portfolio Dashboard
          </span>
          <h1 className="text-lg font-semibold text-slate-100">
            Greeks Cockpit
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <span
            className={`text-[10px] uppercase tracking-[0.2em] ${sourceColor}`}
            title={
              dataSource === "Live"
                ? "Force scores from /classify"
                : dataSource === "Loading"
                  ? "Fetching classification…"
                  : "Quant service unreachable — rendering mock data"
            }
          >
            ● {dataSource}
          </span>
          <button
            type="button"
            onClick={() => setShowDialog(true)}
            className="rounded-md border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-medium text-sky-300 transition hover:bg-sky-500/20"
          >
            + Add Position
          </button>
        </div>
      </header>

      <div className="flex flex-col items-center gap-1">
        <PersonalityLabel classification={classification} />
        <span className="text-xs text-slate-500">
          {position.position.qty}x {position.position.ticker}{" "}
          {position.position.expiration} {position.position.strike}
          {position.position.option_type[0].toUpperCase()},{" "}
          {position.position.side}
        </span>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 shadow-[0_0_60px_-30px_rgba(56,189,248,0.5)]">
        <GreekRadar scores={scores} size={480} />
      </div>

      <PlainEnglishReadout classification={classification} />

      <footer className="mt-8 max-w-2xl text-center text-xs text-slate-600">
        Not investment advice. V1 vertical slice — single position at a time;
        multi-position portfolio aggregation ships next.
      </footer>

      {showDialog && (
        <AddPositionDialog
          initial={position}
          onSubmit={(p) => {
            setPosition(p);
            setShowDialog(false);
          }}
          onClose={() => setShowDialog(false)}
        />
      )}
    </main>
  );
}
