import { NextResponse } from "next/server";
import { redis } from "@/lib/redis";

const VALID_ACTIONS = ["pause", "resume"] as const;

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (!body || typeof body !== "object" || !("action" in body)) {
    return NextResponse.json({ error: "Missing 'action' field" }, { status: 400 });
  }

  const action = (body as { action: unknown }).action;
  if (typeof action !== "string" || !VALID_ACTIONS.includes(action as typeof VALID_ACTIONS[number])) {
    return NextResponse.json(
      { error: `Invalid action. Must be one of: ${VALID_ACTIONS.join(", ")}` },
      { status: 400 },
    );
  }

  if (action === "pause") {
    await redis.set("bot:command", "pause");
    await redis.set("bot:status", "paused");
    return NextResponse.json({ ok: true, command: "pause" });
  }

  if (action === "resume") {
    await redis.set("bot:command", "resume");
    await redis.set("bot:status", "idle");
    return NextResponse.json({ ok: true, command: "resume" });
  }

  return NextResponse.json({ error: "Invalid action" }, { status: 400 });
}
