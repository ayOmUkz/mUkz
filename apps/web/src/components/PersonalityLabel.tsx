import type { Classification } from "@/lib/types";

interface Props {
  classification: Classification;
}

export function PersonalityLabel({ classification }: Props) {
  const label =
    classification.qualifier && classification.primary !== "Mixed Exposure"
      ? `${classification.qualifier} ${classification.primary}`
      : classification.primary;

  const confidencePct = Math.round(classification.confidence * 100);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">
        Position Personality
      </div>
      <div className="text-2xl font-semibold text-slate-100">{label}</div>
      <div className="text-xs text-slate-500">
        Confidence {confidencePct}%
      </div>
    </div>
  );
}
