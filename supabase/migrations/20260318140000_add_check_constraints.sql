-- Add CHECK constraints for data integrity

-- Signals table
ALTER TABLE signals
  ADD CONSTRAINT check_confidence_range
    CHECK (confidence >= 0.0 AND confidence <= 1.0),
  ADD CONSTRAINT check_signal_direction
    CHECK (direction IN ('LONG', 'SHORT')),
  ADD CONSTRAINT check_signal_strategy
    CHECK (strategy IN ('news_sentiment', 'technical_confluence', 'volume_spike')),
  ADD CONSTRAINT check_signal_status
    CHECK (status IN ('open', 'won', 'lost', 'stopped', 'expired', 'cancelled')),
  ADD CONSTRAINT check_signal_entry_price_positive
    CHECK (entry_price > 0),
  ADD CONSTRAINT check_signal_target_price_positive
    CHECK (target_price > 0),
  ADD CONSTRAINT check_signal_stop_price_positive
    CHECK (stop_price > 0),
  ADD CONSTRAINT check_signal_risk_reward_positive
    CHECK (risk_reward > 0);

-- Trades table
ALTER TABLE trades
  ADD CONSTRAINT check_trade_direction
    CHECK (direction IN ('LONG', 'SHORT')),
  ADD CONSTRAINT check_trade_status
    CHECK (status IN ('open', 'closed', 'cancelled')),
  ADD CONSTRAINT check_trade_mode
    CHECK (mode IN ('paper', 'live')),
  ADD CONSTRAINT check_trade_entry_price_positive
    CHECK (entry_price > 0),
  ADD CONSTRAINT check_trade_size_usd_positive
    CHECK (size_usd > 0),
  ADD CONSTRAINT check_trade_exit_price_positive
    CHECK (exit_price IS NULL OR exit_price > 0);

-- Equity snapshots
ALTER TABLE equity_snapshots
  ADD CONSTRAINT check_equity_mode
    CHECK (mode IN ('paper', 'live')),
  ADD CONSTRAINT check_equity_positive
    CHECK (equity_usd > 0);
