-- =====================================================
-- CRBOT DATABASE - INITIAL DATA & SAMPLE DATA
-- For development and testing
-- =====================================================

-- ===================== INSERT SAMPLE BOTS =====================
INSERT INTO bots (name, strategy, exchange, trading_pair, status, initial_capital, max_drawdown_limit, daily_loss_limit, position_size_method, risk_per_trade, total_profit_loss, win_rate, total_trades, winning_trades) VALUES
('Trend Bot Alpha', 'TREND_FOLLOWING', 'BINANCE', 'BTC/USDT', 'RUNNING', 10000.00000000, 10.0, 500.00000000, 'FIXED_PERCENT', 2.0, 1250.50000000, 58.33, 24, 14),
('Breakout Bot Pro', 'BREAKOUT', 'BINANCE', 'ETH/USDT', 'RUNNING', 5000.00000000, 15.0, 300.00000000, 'KELLY', 1.5, 325.75000000, 52.00, 25, 13),
('Elliott Wave Master', 'ELLIOTT_WAVE', 'BINANCE', 'ADA/USDT', 'PAUSED', 8000.00000000, 12.0, 400.00000000, 'ATR', 2.5, -150.25000000, 45.00, 20, 9),
('Grid Trader X', 'GRID_TRADING', 'BINANCE', 'SOL/USDT', 'RUNNING', 3000.00000000, 8.0, 200.00000000, 'FIXED_PERCENT', 1.0, 780.00000000, 65.00, 20, 13),
('Mean Reversion Bot', 'MEAN_REVERSION', 'COINBASE', 'BTC/USD', 'IDLE', 7500.00000000, 12.0, 375.00000000, 'FIXED_PERCENT', 2.2, 450.00000000, 55.00, 22, 12);

-- ===================== INSERT SAMPLE TRADES =====================
INSERT INTO trades (bot_id, symbol, trade_type, status, entry_price, entry_time, entry_quantity, exit_price, exit_time, exit_quantity, stop_loss, take_profit, risk_amount, reward_amount, profit_loss, profit_loss_percent, fees, strategy_used) VALUES
-- BTC Trades (Trend Bot Alpha)
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 'BTC/USDT', 'LONG', 'CLOSED', 43250.50000000, '2025-12-01 10:30:00', 0.15000000, 44000.00000000, '2025-12-01 14:20:00', 0.15000000, 42800.00000000, 45000.00000000, 225.00000000, 1125.00000000, 112.50000000, 0.26, 5.00000000, 'TREND_FOLLOWING'),
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 'BTC/USDT', 'LONG', 'CLOSED', 43500.00000000, '2025-12-02 08:15:00', 0.12000000, 43800.00000000, '2025-12-02 16:45:00', 0.12000000, 43100.00000000, 44500.00000000, 150.00000000, 450.00000000, 36.00000000, 0.07, 3.50000000, 'TREND_FOLLOWING'),
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 'BTC/USDT', 'LONG', 'OPEN', 44100.00000000, '2025-12-04 11:00:00', 0.10000000, NULL, NULL, NULL, 43700.00000000, 45000.00000000, 200.00000000, 475.00000000, NULL, NULL, 2.50000000, 'TREND_FOLLOWING'),

-- ETH Trades (Breakout Bot Pro)
((SELECT id FROM bots WHERE name = 'Breakout Bot Pro'), 'ETH/USDT', 'LONG', 'CLOSED', 2350.25000000, '2025-12-01 12:30:00', 1.50000000, 2400.00000000, '2025-12-01 18:00:00', 1.50000000, 2300.00000000, 2500.00000000, 75.38000000, 225.00000000, 74.63000000, 3.18, 4.00000000, 'BREAKOUT'),
((SELECT id FROM bots WHERE name = 'Breakout Bot Pro'), 'ETH/USDT', 'LONG', 'CLOSED', 2375.00000000, '2025-12-02 09:45:00', 1.25000000, 2350.00000000, '2025-12-02 14:15:00', 1.25000000, 2330.00000000, 2450.00000000, 56.25000000, 93.75000000, -31.25000000, -1.32, 3.50000000, 'BREAKOUT'),
((SELECT id FROM bots WHERE name = 'Breakout Bot Pro'), 'ETH/USDT', 'SHORT', 'OPEN', 2420.50000000, '2025-12-04 13:20:00', 1.00000000, NULL, NULL, NULL, 2450.00000000, 2350.00000000, 30.50000000, 70.50000000, NULL, NULL, 2.00000000, 'BREAKOUT'),

-- ADA Trades (Elliott Wave Master)
((SELECT id FROM bots WHERE name = 'Elliott Wave Master'), 'ADA/USDT', 'LONG', 'CLOSED', 0.98500000, '2025-12-01 15:10:00', 500.00000000, 0.96200000, '2025-12-02 10:30:00', 500.00000000, 0.96000000, 1.05000000, 125.00000000, 325.00000000, -114.00000000, -11.55, 5.00000000, 'ELLIOTT_WAVE'),

-- SOL Trades (Grid Trader X)
((SELECT id FROM bots WHERE name = 'Grid Trader X'), 'SOL/USDT', 'LONG', 'CLOSED', 175.50000000, '2025-12-01 11:00:00', 12.50000000, 182.00000000, '2025-12-02 09:30:00', 12.50000000, 170.00000000, 195.00000000, 68.75000000, 206.25000000, 80.50000000, 1.17, 3.00000000, 'GRID_TRADING'),
((SELECT id FROM bots WHERE name = 'Grid Trader X'), 'SOL/USDT', 'LONG', 'CLOSED', 180.25000000, '2025-12-02 14:15:00', 10.00000000, 188.75000000, '2025-12-03 10:00:00', 10.00000000, 175.00000000, 200.00000000, 52.50000000, 200.00000000, 85.00000000, 1.24, 2.50000000, 'GRID_TRADING');

-- ===================== INSERT STRATEGY PERFORMANCE =====================
INSERT INTO strategy_performance (bot_id, strategy_name, period_start, period_end, trades_count, winning_trades, losing_trades, total_profit_loss, win_rate, profit_factor, sharpe_ratio, sortino_ratio, max_drawdown, average_win, average_loss, largest_win, largest_loss, consecutive_wins, consecutive_losses) VALUES
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 'TREND_FOLLOWING', '2025-11-01', '2025-12-05', 24, 14, 10, 1250.50000000, 58.33, 2.45, 1.85, 2.12, 8.5, 125.50000000, -95.25000000, 250.00000000, -180.50000000, 3, 2),
((SELECT id FROM bots WHERE name = 'Breakout Bot Pro'), 'BREAKOUT', '2025-11-01', '2025-12-05', 25, 13, 12, 325.75000000, 52.00, 1.92, 1.45, 1.68, 11.2, 78.50000000, -85.75000000, 200.00000000, -145.25000000, 2, 2),
((SELECT id FROM bots WHERE name = 'Elliott Wave Master'), 'ELLIOTT_WAVE', '2025-11-01', '2025-12-05', 20, 9, 11, -150.25000000, 45.00, 0.85, 0.65, 0.72, 15.8, 85.00000000, -125.50000000, 200.00000000, -250.75000000, 1, 3),
((SELECT id FROM bots WHERE name = 'Grid Trader X'), 'GRID_TRADING', '2025-11-01', '2025-12-05', 20, 13, 7, 780.00000000, 65.00, 3.15, 2.25, 2.65, 6.2, 95.50000000, -65.75000000, 180.00000000, -120.50000000, 4, 1),
((SELECT id FROM bots WHERE name = 'Mean Reversion Bot'), 'MEAN_REVERSION', '2025-11-01', '2025-12-05', 22, 12, 10, 450.00000000, 54.55, 2.15, 1.95, 2.35, 9.8, 105.00000000, -75.00000000, 225.00000000, -150.00000000, 3, 2);

-- ===================== INSERT BOT METRICS (Latest) =====================
INSERT INTO bot_metrics (bot_id, equity, cash, positions_value, daily_pnl, cumulative_pnl, current_drawdown, max_drawdown) VALUES
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 11250.50000000, 5000.00000000, 6250.50000000, 125.50000000, 1250.50000000, 2.5, 8.5),
((SELECT id FROM bots WHERE name = 'Breakout Bot Pro'), 5325.75000000, 2500.00000000, 2825.75000000, 45.75000000, 325.75000000, 3.8, 11.2),
((SELECT id FROM bots WHERE name = 'Elliott Wave Master'), 7849.75000000, 4000.00000000, 3849.75000000, -50.25000000, -150.25000000, 6.5, 15.8),
((SELECT id FROM bots WHERE name = 'Grid Trader X'), 3780.00000000, 1500.00000000, 2280.00000000, 80.00000000, 780.00000000, 2.1, 6.2),
((SELECT id FROM bots WHERE name = 'Mean Reversion Bot'), 7950.00000000, 3500.00000000, 4450.00000000, 50.00000000, 450.00000000, 3.2, 9.8);

-- ===================== INSERT RISK EVENTS =====================
INSERT INTO risk_events (bot_id, event_type, risk_level, description, threshold_value, current_value, resolved) VALUES
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 'DRAWDOWN_WARNING', 'MEDIUM', 'Current drawdown approaching 10% limit', 10.00000000, 8.50000000, FALSE),
((SELECT id FROM bots WHERE name = 'Elliott Wave Master'), 'DRAWDOWN_ALERT', 'HIGH', 'Drawdown exceeded 15% threshold', 12.00000000, 15.80000000, FALSE),
((SELECT id FROM bots WHERE name = 'Elliott Wave Master'), 'DAILY_LOSS_LIMIT', 'HIGH', 'Daily loss limit approaching', 400.00000000, 350.25000000, FALSE),
((SELECT id FROM bots WHERE name = 'Breakout Bot Pro'), 'CORRELATION_WARNING', 'LOW', 'High correlation detected between positions', 0.85000000, 0.82000000, TRUE);

-- ===================== INSERT EQUITY CURVE DATA =====================
INSERT INTO equity_curve (bot_id, equity_value, cash_value, recorded_at) VALUES
-- Sample data for last 30 days (Trend Bot Alpha)
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 10000.00000000, 5000.00000000, '2025-11-05 00:00:00'),
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 10150.50000000, 5000.00000000, '2025-11-06 00:00:00'),
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 10200.75000000, 5000.00000000, '2025-11-07 00:00:00'),
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 10050.25000000, 5000.00000000, '2025-11-08 00:00:00'),
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 10350.00000000, 5000.00000000, '2025-11-09 00:00:00'),
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 10500.50000000, 5000.00000000, '2025-11-10 00:00:00'),
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 11050.50000000, 5000.00000000, '2025-12-01 00:00:00'),
((SELECT id FROM bots WHERE name = 'Trend Bot Alpha'), 11250.50000000, 5000.00000000, '2025-12-05 00:00:00');

-- Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_trades;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_strategy_comparison;
