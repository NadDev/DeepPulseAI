# CRBot - Crypto Trading Bot Dashboard

L'application complète est maintenant **PRÊTE À L'EMPLOI** ! ✅

## Lancement Rapide

### Option 1: Batch (RECOMMANDÉ pour Windows)
Double-cliquez sur : `RUN_APP.bat`

Cela ouvrira deux fenêtres:
- **Backend**: http://127.0.0.1:8002
- **Frontend**: http://localhost:3000

### Option 2: PowerShell
```powershell
.\start-all.ps1
```

### Option 3: Manuel (Python)
```bash
# Fenêtre 1 - Backend
.venv\Scripts\python start_backend.py

# Fenêtre 2 - Frontend
.venv\Scripts\python start_frontend.py
```

## URLs d'Accès

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:3000/dashboard-live.html |
| **Charts & Analysis** | http://localhost:3000/charts.html |
| **API Backend** | http://127.0.0.1:8002 |
| **API Documentation** | http://127.0.0.1:8002/docs |

## Fonctionnalités Disponibles

### Dashboard Principal (dashboard-live.html)
✅ 4 KPI Cards (Portfolio Value, Daily P&L, Win Rate, Max Drawdown)
✅ Equity Curve Chart (rendement cumulatif)
✅ Active Bots List (status en temps réel)
✅ Recent Trades Table (historique des trades)
✅ Language Selector (FR, EN, avec localStorage)
✅ Auto-refresh toutes les 10 secondes

### Charts & Technical Analysis (charts.html)
✅ Candlestick Chart (OHLC + volume)
✅ Moving Averages Chart (SMA 20, 50, 200)
✅ Volume Bars (volume de trading)
✅ Price Distribution (histogramme)
✅ Global Crypto Selector (BTC, ETH, etc.)
✅ Crypto Analysis Block (Trend, Sentiment, Social Mentions)
✅ Reputation Meter + Market Metrics
✅ Internationalization (FR/EN)

## Endpoints API Disponibles (42 endpoints)

### Health & Status
- `GET /api/health` - Santé du service
- `GET /api/ready` - Ready check

### Portfolio
- `GET /api/portfolio/summary` - Résumé du portefeuille
- `GET /api/trades` - Tous les trades
- `GET /api/portfolio/equity-curve?days=30` - Courbe d'équité

### Bots Management
- `GET /api/bots/list` - Liste des bots
- `GET /api/bots/{bot_id}` - Détails d'un bot
- `POST /api/bots/{bot_id}/start` - Démarrer bot
- `POST /api/bots/{bot_id}/pause` - Pause bot
- `POST /api/bots/{bot_id}/stop` - Arrêter bot
- `GET /api/bots/{bot_id}/performance` - Performance du bot

### Crypto Data (ARCH 1 - NEW!)
- `GET /api/crypto/prices` - Prix actuels
- `GET /api/crypto/chart` - Données OHLCV
- `GET /api/crypto/{symbol}/data` - Données détaillées
- `GET /api/crypto/{symbol}/analysis` - Analyse crypto
- `GET /api/data/market/{symbol}` - Données de marché
- `GET /api/data/candles/{symbol}` - Bougies OHLCV

### Technical Indicators (ARCH 1 - NEW!)
- `GET /api/indicators/{symbol}/rsi` - RSI Indicator
- `GET /api/indicators/{symbol}/macd` - MACD
- `GET /api/indicators/{symbol}/bollinger` - Bollinger Bands
- `GET /api/indicators/{symbol}/ema` - EMA
- `GET /api/indicators/{symbol}/all` - All Indicators

### Sentiment Analysis (ARCH 1 - NEW!)
- `GET /api/sentiment/{symbol}` - Analyse sentiment
- `GET /api/sentiment/{symbol}/fear-greed` - Fear & Greed Index
- `GET /api/sentiment/{symbol}/whale-alerts` - Whale Alerts

### Trading
- `GET /api/trades` - Tous les trades
- `GET /api/trades/list` - Liste des trades
- `GET /api/trades/{trade_id}` - Détails trade
- `POST /api/trades/create` - Créer un trade
- `PUT /api/trades/{trade_id}/close` - Clôturer un trade

### Reports
- `GET /api/reports/dashboard` - Rapport dashboard
- `GET /api/reports/trades` - Rapport trades
- `GET /api/reports/strategies` - Rapport stratégies
- `GET /api/reports/performance` - Rapport performance

### Risk Management
- `GET /api/risk-events` - Événements de risque
- `GET /api/risk-summary` - Résumé du risque

### Internationalization
- `GET /api/translations/{lang}` - Traductions dynamiques
- `GET /api/translations` - Métadonnées langues

## Architecture Implémentée (ARCH 1)

### Services Backend
```
app/services/
├── market_data.py      - Collecteur de données de marché (Binance, Coingecko)
├── technical_analysis.py - Indicateurs techniques (RSI, MACD, Bollinger, EMA, ATR)
├── sentiment.py        - Analyse de sentiment (Social, News, Fear & Greed)
└── strategies/         - Moteur de stratégies (à venir)
```

### Endpoints ARCH 1
- **12 nouveaux endpoints** pour indicateurs techniques et sentiment
- **Cache avec TTL** pour les performances
- **Fallback Coingecko** pour les données crypto
- **Intégration Binance API** pour les bougies

## Données de Test

L'application utilise :
- **SQLite** local pour le stockage (crbot.db)
- **Données de démo** avec valeurs réalistes
- **Appels API réels** vers Binance et Coingecko
- **Auto-refresh toutes les 10 secondes**

## Notes Importantes

1. **Ports utilisés:**
   - Backend: `8002` (FastAPI)
   - Frontend: `3000` (HTTP Server)

2. **Dépendances principales:**
   - FastAPI + Uvicorn
   - SQLAlchemy + SQLite
   - Chart.js (visualisation)
   - TailwindCSS (styling)
   - httpx (requêtes HTTP async)

3. **Langues supportées:**
   - Français (FR) ✅
   - Anglais (EN) ✅
   - Allemand, Espagnol, Chinois (framework prêt pour Phase 2)

4. **Progression Globale:**
   - **13/30 tâches architecturales complétées (43%)**
   - **42 endpoints API fonctionnels**
   - **6 tables de base de données**
   - **7 pages frontend**

## Prochaines Étapes

- ARCH 2: ML Engine (LSTM, Transformer)
- ARCH 3: Bot Strategy Engine (5 stratégies)
- ARCH 4: Broker Integration
- ARCH 5: Execution & Risk Manager
- ARCH 6: Data Pipeline Real-time (WebSocket)
- ARCH 7: Dashboard Enhancement

---

**Créé avec Python, FastAPI, SQLite, Chart.js et TailwindCSS** 🚀
