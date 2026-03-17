import { NextResponse } from "next/server";
import { redis } from "@/lib/redis";
import type { BotStatus } from "@/lib/types";

export async function GET() {
  const [status, tradeMode, lastRun, equity, activePairs, prices] =
    await Promise.all([
      redis.get<string>("bot:status"),
      redis.get<string>("bot:trade_mode"),
      redis.get<string>("bot:last_run"),
      redis.get<string>("bot:paper:equity"),
      redis.get<string>("pairs:active"),
      redis.hgetall("pairs:prices"),
    ]);

  const botStatus: BotStatus = {
    status: (status as BotStatus["status"]) ?? "idle",
    trade_mode: (tradeMode as BotStatus["trade_mode"]) ?? "paper",
    last_run: lastRun,
    paper_equity: equity ? parseFloat(equity) : null,
  };

  return NextResponse.json({
    bot: botStatus,
    active_pairs: activePairs ? JSON.parse(activePairs) : [],
    prices: prices ?? {},
  });
}
