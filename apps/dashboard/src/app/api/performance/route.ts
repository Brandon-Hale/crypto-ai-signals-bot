import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import type { PerformanceSummary } from "@/lib/types";

export async function GET() {
  const { data, error } = await supabase
    .from("performance_summary")
    .select("*")
    .order("updated_at", { ascending: false });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json((data as PerformanceSummary[]) ?? []);
}
