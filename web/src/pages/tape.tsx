import { FormEvent, useState } from "react";
import type { Tape } from "@/lib/api";
import { fetchJson } from "@/lib/api";
import { TapeTable } from "@/components/TapeTable";

export default function TapePage() {
  const [ticker, setTicker] = useState("");
  const [tape, setTape] = useState<Tape | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      setTape(await fetchJson<Tape>(`/tape?ticker=${ticker.trim().toUpperCase()}`));
    } catch (e) {
      setTape(null);
      setError(String(e));
    }
  };

  return (
    <>
      <section className="card">
        <h3>Dark-pool tape</h3>
        <form onSubmit={load} className="tape-form">
          <input
            value={ticker}
            onChange={(event) => setTicker(event.target.value)}
            placeholder="Ticker, e.g. NVDA"
            aria-label="Ticker"
          />
          <button type="submit" disabled={ticker.trim().length === 0}>
            Load
          </button>
        </form>
        {error ? <p className="muted">Could not load: {error}</p> : null}
        {tape ? <TapeTable prints={tape.prints} /> : null}
      </section>
    </>
  );
}
