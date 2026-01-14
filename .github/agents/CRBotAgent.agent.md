# 🤖 CRBot Custom Agent - Instructions

## 1️⃣ ARCHITECTURE SYSTEM
Tu travailles sur DeepPulseAI, une plateforme de day trading crypto avec:

### Backend
- **Framework:** FastAPI + SQLAlchemy ORM
- **Database:** Railway PostgreSQL (user_id filtering for multi-tenancy)
- **External APIs:** Binance (market data), DeepSeek (LLM), Supabase (auth JWT)
- **Key Services:**
  - BotEngine: 60s monitoring loop, strategy execution
  - RiskManager: Trade validation (position size, duplicates, daily limits)
  - 9 Strategies: All inherit from BaseStrategy (get_signal_direction, should_exit)
  - MLEngine: LSTM predictions with TensorFlow
  - AIAgent: DeepSeek analysis, autonomous bot creation

### Frontend
- React 18 + Vite, deployed on Vercel
- Supabase Auth (JWT tokens injected in API calls)
- Components: BotManager, Portfolio, Dashboard, AISettings

### Database Schema
- `bots` (id UUID, user_id UUID, strategy, status, config JSONB, symbols JSONB)
- `trades` (id UUID, user_id UUID, bot_id FK, symbol, entry/exit prices, status)
- `portfolios` (user_id UUID UNIQUE, cash_balance, total_value, daily/total_pnl)

---

## 2️⃣ RECENT BUGS FIXED (MEMORY)
You've just applied 5 critical fixes:

1. ✅ Grid Trading: Added state validation (SELL only if BUY exists)
2. ✅ RiskManager: Duplicate check now includes CLOSING status
3. ✅ BotEngine: Position size clamped to 25% max
4. ✅ BotEngine: Fallback amount enforces ABSOLUTE limits
5. ✅ Logging: Added [SIGNAL], [BLOCKED], [BUY-EXEC], [SELL-EXEC] prefixes

**Commit:** `5f05a87` - "Apply 5 critical Bug #2 fixes with comprehensive logging"

---

## 3️⃣ CODE PATTERNS (APPLY ALWAYS)

### Logging Pattern
```python
logger.info(f"📊 [SIGNAL] {bot_name} | {symbol} | {action}")
logger.info(f"⚠️ [BLOCKED] {symbol}: {reason}")
logger.info(f"✅ [BUY-EXEC] {symbol} | Qty: {qty} | Cost: ${cost}")