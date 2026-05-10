import type { Classification } from "@/lib/types";

interface Props {
  classification: Classification;
}

export function PlainEnglishReadout({ classification }: Props) {
  return (
    <div className="max-w-2xl rounded-lg border border-slate-800 bg-slate-900/40 px-5 py-4 text-sm leading-relaxed text-slate-300">
      {classification.readout}
    </div>
  );
}
