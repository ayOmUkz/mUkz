import type { ClassifyResponse, EnrichedPosition } from "./types";

const QUANT_SERVICE_URL =
  process.env.QUANT_SERVICE_URL ||
  process.env.NEXT_PUBLIC_QUANT_SERVICE_URL ||
  "http://localhost:8000";

export async function classifyPosition(
  position: EnrichedPosition,
): Promise<ClassifyResponse | null> {
  try {
    const res = await fetch(`${QUANT_SERVICE_URL}/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(position),
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as ClassifyResponse;
  } catch {
    return null;
  }
}
