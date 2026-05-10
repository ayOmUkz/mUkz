import { GreekRadar } from "@/components/GreekRadar";
import { PersonalityLabel } from "@/components/PersonalityLabel";
import { PlainEnglishReadout } from "@/components/PlainEnglishReadout";
import { MOCK_CLASSIFICATION, MOCK_FORCE_SCORES } from "@/lib/mock-data";

export default function Home() {
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
        <button
          type="button"
          className="rounded-md border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-medium text-sky-300 transition hover:bg-sky-500/20"
        >
          + Add Position
        </button>
      </header>

      <PersonalityLabel classification={MOCK_CLASSIFICATION} />

      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 shadow-[0_0_60px_-30px_rgba(56,189,248,0.5)]">
        <GreekRadar scores={MOCK_FORCE_SCORES} size={480} />
      </div>

      <PlainEnglishReadout classification={MOCK_CLASSIFICATION} />

      <footer className="mt-8 max-w-2xl text-center text-xs text-slate-600">
        Not investment advice. Data shown is mock for the V1 vertical slice;
        live Polygon chains wire in the next iteration.
      </footer>
    </main>
  );
}
