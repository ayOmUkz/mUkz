import { NextResponse } from "next/server";

import { classifyPosition } from "@/lib/quant-client";
import type { EnrichedPosition } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  let position: EnrichedPosition;
  try {
    position = (await req.json()) as EnrichedPosition;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const result = await classifyPosition(position);
  if (!result) {
    return NextResponse.json(
      { error: "Quant service unreachable" },
      { status: 503 },
    );
  }
  return NextResponse.json(result);
}
