# Testing Checklist - Bot Trading Execution Fixes

**Test Date:** _____________  
**Tester:** _____________  
**Bot Name:** _____________  
**Strategy:** _____________  

---

## Pre-Test Setup

- [ ] Backend running with latest code (`git pull && npm install && pip install -r requirements.txt`)
- [ ] PostgreSQL database connected (check Railway console)
- [ ] Frontend running (Vercel or local Vite)
- [ ] Bot created and configured
- [ ] Market data available (can see Binance prices)
- [ ] Paper trading enabled (check bot config)
- [ ] Console/logs visible (backend logs should show INFO level)

---

## Test 1: Signal Generation

**Expected Behavior:** Bot generates BUY/SELL signals based on strategy

### Steps:
1. Start monitoring backend logs
2. Wait for bot cycle (should see logs every 60 seconds)
3. Watch for `📊 [SIGNAL]` log entries

### Verification:
- [ ] See `📊 [SIGNAL] {bot_name} | {symbol} | BUY` in logs
- [ ] Log includes strategy name
- [ ] Signal matches market conditions (e.g., price in lower band = BUY)
- [ ] Signals appear every 60 seconds per symbol

### Success Criteria:
✅ Signals are generated regularly  
❌ No signals appearing → Check if strategy is enabled and has config

---

## Test 2: Buy Execution

**Expected Behavior:** When BUY signal generated, trade is created

### Steps:
1. Trigger a BUY signal (or wait for one)
2. Check for `✅ [BUY-EXEC]` log
3. Verify trade in database

### Verification Log Should Show:
```
✅ [BUY-EXEC] {bot_name} | {symbol}
├─ Trade ID: {UUID first 8 chars}
├─ Price: ${current_price}
├─ Quantity: {qty}
├─ Cost: ${cost}
├─ Portfolio: ${before} → ${after}
├─ SL: ${stop_loss} ({pct}%)
├─ TP: ${take_profit} ({pct}%)
└─ 🤖 AI: {AI result or N/A}
```

### Verification Database:
- [ ] New Trade record created
- [ ] Trade.status = "OPEN"
- [ ] Trade.entry_price = signal price
- [ ] Trade.stop_loss_price has value
- [ ] Trade.take_profit_price has value
- [ ] Trade.side = "BUY"

### Verification Portfolio:
- [ ] Portfolio.cash_balance decreased by trade cost
- [ ] Portfolio.total_value updated

### Success Criteria:
✅ Trade created with TP/SL set  
⚠️ Trade created but no TP → Bug: TP not calculated
❌ Trade not created → Check RiskManager logs for `[BLOCKED]`

---

## Test 3: Take Profit Closure

**Expected Behavior:** When price reaches TP level, position closes automatically

### Steps:
1. Wait for BUY trade to execute
2. Note the entry price and TP level
3. Monitor logs for price movements
4. Wait for price to reach or exceed TP level

### Verification (Every 60 Seconds):
- [ ] See `📊 [POS-CHECK] {symbol} | 1 open(s) @ ${current_price}`
- [ ] If price < TP: See `📊 [TP-WATCH] {symbol} | ${price} → TP ${tp_price}`
- [ ] If price ≥ TP: See `💰 [TP-TRIGGER] {symbol} | Price ${price} ≥ TP ${tp_price}`

### Verification After TP Trigger:
- [ ] See `✅ [CLOSE-EXEC] {symbol}` with:
  - Trade ID matching BUY trade
  - Entry price and exit price
  - PnL showing profit (positive value)
  - Reason: "Take Profit"
- [ ] Trade.status changed to "CLOSED"
- [ ] Trade.exit_price = price at closure
- [ ] Trade.exit_time = closure time
- [ ] Portfolio.cash_balance increased by PnL amount

### Success Criteria:
✅ Price reaches TP and position closes  
⚠️ Price reaches TP but position stays open → [TP-TRIGGER] never logs
❌ [POS-CHECK] not appearing → Position monitoring loop not running

---

## Test 4: Stop Loss Closure

**Expected Behavior:** When price drops to SL level, position closes

### Steps:
1. Same as Test 3, but trigger a STOP LOSS instead of TP
2. Watch for price to hit SL level

### Verification:
- [ ] See `📊 [POS-CHECK]` log every 60 seconds
- [ ] When price hits SL: See `🛑 [SL-TRIGGER] {symbol} | Price ${price} ≤ SL ${sl}`
- [ ] See `✅ [CLOSE-EXEC]` log with loss (negative PnL)
- [ ] Trade.status = "CLOSED"
- [ ] Portfolio.cash_balance adjusted by PnL (loss)

### Success Criteria:
✅ Position closes at stop loss  
❌ Position stays open past SL → Bug similar to TP issue

---

## Test 5: Grid Trading State Validation

**Expected Behavior:** Grid strategy only SELL when there's an open BUY

### Steps:
1. Configure bot with Grid Trading strategy
2. Monitor for BUY signals
3. After BUY executes, watch for price movement
4. If price moves to upper band (should trigger SELL)

### Verification:
- [ ] Grid strategy generates BUY when price in lower 33% of band
- [ ] Grid strategy generates SELL when price in upper 33% AND open BUY exists
- [ ] If no open BUY: See log `⚠️  [SKIP] No open BUY position to SELL`
- [ ] Grid never generates orphaned SELL signals

### Success Criteria:
✅ SELL only when BUY exists (proper state machine)  
❌ SELL without BUY → Grid state validation not working

---

## Test 6: Risk Management

**Expected Behavior:** Bot respects position size limits and duplicate checks

### Steps:
1. Try to create multiple BUY signals on same symbol
2. Monitor for `⚠️ [BLOCKED]` logs

### Verification:
- [ ] First BUY executes (trade created)
- [ ] Subsequent BUY signals for same symbol are blocked
- [ ] See log: `⚠️ [BLOCKED] {symbol} BUY: Duplicate open position exists`
- [ ] Position size never exceeds 25% of portfolio
- [ ] If position would exceed: See `⚠️ [POS-LIMIT]` log

### Success Criteria:
✅ Duplicates prevented, position sizes capped  
❌ Multiple opens for same symbol → Risk validation broken

---

## Test 7: Portfolio Balance Tracking

**Expected Behavior:** Portfolio values update correctly with trades

### Monitoring:
- [ ] Before any trades: note `portfolio.cash_balance`
- [ ] After BUY: balance decreases by `cost`
- [ ] After SELL: balance increases by `pnl` (not gross proceeds!)
- [ ] Portfolio.total_pnl accumulates all PnL

### Math Verification:
```
Initial: $10,000
BUY: 10 BTC @ $1000 → Cost $10,000 → Balance $0
SELL: 10 BTC @ $1050 → PnL $500 → Balance $500 (NOT $10,500!)
Final: Portfolio shows $500 cash, +$500 PnL
```

### Success Criteria:
✅ Balance calculations correct  
❌ Balance wrong after trades → PnL calculation bug

---

## Test 8: Database Enum Integrity

**Expected Behavior:** No errors about "CLOSING" status

### Verification:
- [ ] No error logs containing "CLOSING"
- [ ] No PostgreSQL errors about invalid enum value
- [ ] Trade.status only values: OPEN, CLOSED, ERROR
- [ ] RiskManager only checks Trade.status == "OPEN"

### Success Criteria:
✅ No enum errors in logs  
❌ CLOSING error appears → Enum fix not applied

---

## Test 9: AI Validation (If Enabled)

**Expected Behavior:** AI validation can block trades

### Steps:
1. Enable AI validation in bot config
2. Set AI min confidence to high value (e.g., 80%)
3. Monitor for `🤖 AI Analysis` logs
4. Watch for AI blocks when confidence is low

### Verification:
- [ ] See `🤖 AI Analysis for {symbol}: {action} (confidence: {%}%)`
- [ ] If confidence < threshold: See `🤖 AI BLOCKED {signal}`
- [ ] If confidence >= threshold and agrees: Trade executes
- [ ] AI logs appear before trade execution

### Success Criteria:
✅ AI validation works correctly  
⚠️ AI disabled → Optional feature, test only if enabled

---

## Test 10: Complete Trade Cycle

**Full Workflow:** BUY → HOLD → TP/SL → CLOSE

### Timeline:
1. **T+0min:** Signal detected → `📊 [SIGNAL]`
2. **T+1min:** BUY executed → `✅ [BUY-EXEC]`
3. **T+1-60min:** Position monitored → `📊 [POS-CHECK]` every 60s
4. **T+X min:** TP/SL hit → `💰 [TP-TRIGGER]` or `🛑 [SL-TRIGGER]`
5. **T+X+1min:** Position closed → `✅ [CLOSE-EXEC]`
6. **T+X+2min:** Portfolio updated with PnL

### Success Criteria:
✅ All steps complete in correct order  
❌ Any step missing → Debug using logs from Tests 1-9

---

## Troubleshooting

### Problem: No logs appearing
**Check:**
- Backend running? (`ps aux | grep python` on Linux, or Task Manager on Windows)
- Logs at INFO level? (Check `logger.setLevel()` in bot_engine.py)
- Bot actually monitoring? (Check bot status in frontend)

### Problem: Trades not executing
**Check:**
- RiskManager allowing trade? (Look for `⚠️ [BLOCKED]` log)
- Signal being generated? (Look for `📊 [SIGNAL]` log)
- Risk percentage too low? (Check bot config)
- Portfolio has cash? (Verify portfolio.cash_balance > 0)

### Problem: Positions not closing
**Check:**
- `📊 [POS-CHECK]` appearing? (Position check running)
- `📊 [TP-WATCH]` showing distance to TP? (Values correct?)
- `💰 [TP-TRIGGER]` appearing when price hits TP? (Condition met?)
- `✅ [CLOSE-EXEC]` appearing? (_close_position executing?)

### Problem: Portfolio balance incorrect
**Check:**
- PnL calculation: `(exit_price - entry_price) * quantity`
- Is it adding only PnL, not gross proceeds?
- Check Trade records for correct entry/exit prices
- Check Portfolio.total_pnl accumulation

---

## Log Filtering Tips

To focus on specific issues:

```bash
# All trading activity
grep -E "\[SIGNAL\]|\[BUY-EXEC\]|\[TP-TRIGGER\]|\[CLOSE-EXEC\]" logs.txt

# Only blocked trades
grep "\[BLOCKED\]" logs.txt

# Position monitoring
grep "\[POS-CHECK\]" logs.txt

# TP/SL closure
grep -E "\[TP-TRIGGER\]|\[SL-TRIGGER\]" logs.txt

# Errors
grep "❌\|ERROR\|error" logs.txt
```

---

## Success = All Tests Pass ✅

If all 10 tests pass with success criteria met, then:

1. ✅ Bot trading execution is fixed
2. ✅ Position closure (TP/SL) working
3. ✅ Risk management enforced
4. ✅ Grid trading state machine correct
5. ✅ Database integrity maintained
6. ✅ Portfolio tracking accurate
7. ✅ Logging clear and visible
8. ✅ Ready for production trading

**Next Steps:**
- Monitor for 24+ hours with small position sizes
- Verify PnL calculations match manual math
- Test with multiple bots simultaneously
- Monitor AI agent decisions (if enabled)

