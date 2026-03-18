import { NextResponse } from "next/server";
import { redis } from "@/lib/redis";

export async function POST(request: Request) {
  const { action } = (await request.json()) as { action: string };

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
