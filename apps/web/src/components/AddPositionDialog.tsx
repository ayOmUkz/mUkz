"use client";

import { useState } from "react";

import type { EnrichedPosition, OptionType, Side } from "@/lib/types";

interface Props {
  initial: EnrichedPosition;
  onSubmit: (position: EnrichedPosition) => void;
  onClose: () => void;
}

export function AddPositionDialog({ initial, onSubmit, onClose }: Props) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [form, setForm] = useState<EnrichedPosition>(initial);

  const set = <K extends keyof EnrichedPosition["position"]>(
    key: K,
    value: EnrichedPosition["position"][K],
  ) => setForm((p) => ({ ...p, position: { ...p.position, [key]: value } }));

  const setCtx = <K extends keyof EnrichedPosition["context"]>(
    key: K,
    value: EnrichedPosition["context"][K],
  ) => setForm((p) => ({ ...p, context: { ...p.context, [key]: value } }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 px-4 py-12 backdrop-blur"
      onClick={onClose}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="w-full max-w-xl rounded-xl border border-slate-800 bg-slate-950/95 p-6 shadow-2xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">Add Position</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-500 transition hover:text-slate-200"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <section className="mb-4 grid grid-cols-2 gap-3">
          <Field label="Ticker">
            <input
              required
              value={form.position.ticker}
              onChange={(e) => set("ticker", e.target.value.toUpperCase())}
              className={inputCls}
            />
          </Field>
          <Field label="Expiration">
            <input
              required
              type="date"
              value={form.position.expiration}
              onChange={(e) => set("expiration", e.target.value)}
              className={inputCls}
            />
          </Field>
          <Field label="Strike">
            <input
              required
              type="number"
              step="0.5"
              value={form.position.strike}
              onChange={(e) => set("strike", parseFloat(e.target.value))}
              className={inputCls}
            />
          </Field>
          <Field label="Type">
            <select
              value={form.position.option_type}
              onChange={(e) => set("option_type", e.target.value as OptionType)}
              className={inputCls}
            >
              <option value="call">Call</option>
              <option value="put">Put</option>
            </select>
          </Field>
          <Field label="Side">
            <select
              value={form.position.side}
              onChange={(e) => set("side", e.target.value as Side)}
              className={inputCls}
            >
              <option value="long">Long</option>
              <option value="short">Short</option>
            </select>
          </Field>
          <Field label="Quantity">
            <input
              required
              type="number"
              min="1"
              value={form.position.qty}
              onChange={(e) => set("qty", parseInt(e.target.value, 10))}
              className={inputCls}
            />
          </Field>
          <Field label="Entry price (optional)">
            <input
              type="number"
              step="0.01"
              value={form.position.entry_price ?? ""}
              onChange={(e) =>
                set(
                  "entry_price",
                  e.target.value === "" ? null : parseFloat(e.target.value),
                )
              }
              className={inputCls}
            />
          </Field>
          <Field label="DTE">
            <input
              required
              type="number"
              min="0"
              value={form.context.dte}
              onChange={(e) => setCtx("dte", parseInt(e.target.value, 10))}
              className={inputCls}
            />
          </Field>
        </section>

        <button
          type="button"
          onClick={() => setShowAdvanced((s) => !s)}
          className="mb-3 text-xs uppercase tracking-[0.2em] text-slate-500 transition hover:text-slate-300"
        >
          {showAdvanced ? "▾" : "▸"} Chain data (vendor Greeks)
        </button>

        {showAdvanced && (
          <section className="mb-4 grid grid-cols-2 gap-3 rounded-lg border border-slate-800 bg-slate-900/40 p-3">
            <Field label="Underlying price">
              <input
                type="number"
                step="0.01"
                value={form.context.underlying_price}
                onChange={(e) => setCtx("underlying_price", parseFloat(e.target.value))}
                className={inputCls}
              />
            </Field>
            <Field label="Mid premium">
              <input
                type="number"
                step="0.01"
                value={form.context.mid}
                onChange={(e) => setCtx("mid", parseFloat(e.target.value))}
                className={inputCls}
              />
            </Field>
            <Field label="IV (decimal)">
              <input
                type="number"
                step="0.01"
                value={form.context.iv}
                onChange={(e) => setCtx("iv", parseFloat(e.target.value))}
                className={inputCls}
              />
            </Field>
            <Field label="IV rank (0-100)">
              <input
                type="number"
                min="0"
                max="100"
                value={form.context.iv_rank}
                onChange={(e) => setCtx("iv_rank", parseFloat(e.target.value))}
                className={inputCls}
              />
            </Field>
            <Field label="Delta">
              <input
                type="number"
                step="0.01"
                value={form.context.delta}
                onChange={(e) => setCtx("delta", parseFloat(e.target.value))}
                className={inputCls}
              />
            </Field>
            <Field label="Gamma">
              <input
                type="number"
                step="0.001"
                value={form.context.gamma}
                onChange={(e) => setCtx("gamma", parseFloat(e.target.value))}
                className={inputCls}
              />
            </Field>
            <Field label="Theta">
              <input
                type="number"
                step="0.01"
                value={form.context.theta}
                onChange={(e) => setCtx("theta", parseFloat(e.target.value))}
                className={inputCls}
              />
            </Field>
            <Field label="Vega">
              <input
                type="number"
                step="0.01"
                value={form.context.vega}
                onChange={(e) => setCtx("vega", parseFloat(e.target.value))}
                className={inputCls}
              />
            </Field>
          </section>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-md border border-sky-500/40 bg-sky-500/20 px-4 py-2 text-sm font-medium text-sky-200 transition hover:bg-sky-500/30"
          >
            Classify
          </button>
        </div>

        <p className="mt-3 text-[10px] text-slate-600">
          V1 limitation: vendor Greeks are entered manually until Polygon is
          wired. The bid/ask/OI/volume defaults are reasonable for liquid names.
        </p>
      </form>
    </div>
  );
}

const inputCls =
  "w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 focus:border-sky-500 focus:outline-none";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-[0.15em] text-slate-500">
        {label}
      </span>
      {children}
    </label>
  );
}
