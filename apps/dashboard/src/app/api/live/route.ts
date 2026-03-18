import { NextResponse } from "next/server";
import { redis } from "@/lib/redis";
import type { BotStatus } from "@/lib/types";

export async function GET() {
  const [status, tradeMode, lastRun, equity, heartbeat, activePairs, prices] =
    await Promise.all([
      redis.get<string>("bot:status"),
      redis.get<string>("bot:trade_mode"),
      redis.get<string>("bot:last_run"),
      redis.get<string>("bot:paper:equity"),
      redis.get<string>("bot:heartbeat"),
      redis.get<string>("pairs:active"),
      redis.hgetall("pairs:prices"),
    ]);

  let resolvedStatus: BotStatus["status"];
  if (!heartbeat) {
    resolvedStatus = "stopped";
  } else {
    resolvedStatus = (status as BotStatus["status"]) ?? "idle";
  }

  const botStatus: BotStatus = {
    status: resolvedStatus,
    trade_mode: (tradeMode as BotStatus["trade_mode"]) ?? "paper",
    last_run: lastRun,
    paper_equity: equity ? parseFloat(equity) : null,
  };

  return NextResponse.json({
    bot: botStatus,
    active_pairs: activePairs
      ? Array.isArray(activePairs)
        ? activePairs
        : String(activePairs).split(",").filter(Boolean)
      : [],
    prices: prices ?? {},
  });
}
