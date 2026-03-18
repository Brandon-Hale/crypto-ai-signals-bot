-- Enable RLS on all tables and add read policies for the anon role.
-- The bot writes via the service key (bypasses RLS).
-- The dashboard reads via anon key and needs these SELECT policies.

ALTER TABLE pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE ohlcv_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE equity_snapshots ENABLE ROW LEVEL SECURITY;

-- Allow anonymous reads on all tables (dashboard is read-only)
CREATE POLICY "Allow anon read pairs"
  ON pairs FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon read signals"
  ON signals FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon read trades"
  ON trades FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon read ohlcv_snapshots"
  ON ohlcv_snapshots FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon read performance_summary"
  ON performance_summary FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon read equity_snapshots"
  ON equity_snapshots FOR SELECT TO anon USING (true);
