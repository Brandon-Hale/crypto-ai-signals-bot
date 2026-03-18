-- Enable Realtime on tables the dashboard subscribes to.
ALTER PUBLICATION supabase_realtime ADD TABLE signals;
ALTER PUBLICATION supabase_realtime ADD TABLE trades;
ALTER PUBLICATION supabase_realtime ADD TABLE equity_snapshots;
ALTER PUBLICATION supabase_realtime ADD TABLE performance_summary;
