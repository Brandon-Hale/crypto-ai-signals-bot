import { createClient } from "@supabase/supabase-js";

// Client-side Supabase instance using the anon key (safe for browser).
// Used for Realtime subscriptions.
export const supabaseBrowser = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);
