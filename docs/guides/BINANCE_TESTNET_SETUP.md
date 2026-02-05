# 🧪 Guide Testnet Binance - DeepPulseAI

## ✅ Vérification Conformité

Notre implémentation `BinanceBroker` est **100% conforme** à la documentation officielle Binance:

### URLs (Déjà implémenté)
```python
LIVE_URL = "https://api.binance.com"           # Production
TESTNET_URL = "https://testnet.binance.vision"  # Test
```

### Endpoints supportés ✅
| Endpoint | Usage | Status |
|----------|-------|--------|
| `GET /api/v3/klines` | Candles OHLCV | ✅ Implémenté |
| `GET /api/v3/ticker/24hr` | Ticker 24h | ✅ Implémenté |
| `GET /api/v3/ticker/price` | Prix actuel | ✅ Implémenté |
| `POST /api/v3/order` | Placer ordre | ✅ Implémenté |
| `DELETE /api/v3/order` | Annuler ordre | ✅ Implémenté |
| `GET /api/v3/order` | Status ordre | ✅ Implémenté |
| `GET /api/v3/account` | Balance compte | ✅ Implémenté |
| `GET /api/v3/exchangeInfo` | Info symboles | ✅ Implémenté |

### Authentification ✅
- **HMAC-SHA256** avec timestamp (implémenté dans `_sign_request()`)
- Compatible RSA et Ed25519 (non implémenté mais doc disponible)

---

## 🚀 Comment Tester sur Testnet

### **Étape 1: Créer un compte Testnet**

1. Aller sur: **https://testnet.binance.vision**
2. Se connecter avec GitHub
3. Générer un API Key/Secret depuis le dashboard

### **Étape 2: Configurer dans DeepPulseAI**

Via Settings → Exchanges:
```json
{
  "exchange": "binance",
  "name": "Binance Testnet",
  "api_key_encrypted": "[votre key]",
  "api_secret_encrypted": "[votre secret]",
  "is_active": true,
  "is_default": true,
  "paper_trading": false,  // ❌ False car testnet est déjà un environnement simulé
  "use_testnet": true,     // ✅ Active testnet URL
  "max_trade_size": 1000.0,
  "max_daily_trades": 50
}
```

### **Étape 3: Le BrokerFactory fait le reste**

```python
# backend/app/brokers/factory.py (ligne 105)
broker = BinanceBroker(
    api_key=api_key,
    api_secret=api_secret,
    testnet=config.use_testnet  # ✅ Automatique
)
```

Le broker utilisera automatiquement:
- `https://testnet.binance.vision/api` si `use_testnet=True`
- `https://api.binance.com/api` si `use_testnet=False`

---

## 📋 Caractéristiques Testnet

### Fonds Virtuels
- Balance automatique attribuée à chaque utilisateur (BTC, ETH, USDT, etc.)
- Pas de transfert possible vers production
- **Reset mensuel** (~1x/mois) mais API keys préservées

### Limites
- **Mêmes rate limits** que production (IP, order rate, filters)
- Vérifier avec: `GET /api/v3/exchangeInfo`

### Restrictions
- ❌ Pas d'endpoints `/sapi` (wallet, fiat, etc.)
- ✅ Tous les endpoints `/api` (market data, trading, account)

---

## 🧪 Tests Recommandés

### Phase 1: Market Data (Sans API Key)
```python
# Test candles
candles = await broker.get_candles("BTCUSDT", "1h", 100)

# Test ticker
ticker = await broker.get_ticker("BTCUSDT")

# Test latest price
price = await broker.get_latest_price("BTCUSDT")
```

### Phase 2: Account Data (Avec API Key)
```python
# Test account balance
balance = await broker.get_account_balance()
print(f"USDT: {balance.free_balance}")

# Test symbol info
info = await broker.get_symbol_info("BTCUSDT")
print(f"Min qty: {info.min_quantity}")
```

### Phase 3: Order Execution
```python
# Test LIMIT order
result = await broker.place_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=0.001,
    price=50000.0
)

# Test order status
status = await broker.get_order_status("BTCUSDT", result.order_id)

# Test cancel
await broker.cancel_order("BTCUSDT", result.order_id)
```

---

## 🔐 Modes de Trading Disponibles

| Mode | Description | URL | Fonds |
|------|-------------|-----|-------|
| **Paper Trading** | Simulation locale avec ordre virtuels | Production | Virtuels (app) |
| **Testnet** | Vrai API Binance avec fonds test | `testnet.binance.vision` | Virtuels (Binance) |
| **Live** | Trading réel | `api.binance.com` | Réels |

### Configuration Recommandée

```plaintext
Développement Local:
└── paper_trading=true + use_testnet=false
    → PaperBroker avec LiveDataSource(BinanceBroker production)
    → Pas d'API keys nécessaires

Test Pré-Production:
└── paper_trading=false + use_testnet=true
    → BinanceBroker en mode testnet
    → API keys testnet requises

Production:
└── paper_trading=false + use_testnet=false
    → BinanceBroker en mode live
    → API keys production requises
```

---

## 🐛 Troubleshooting

### Erreur: "Invalid API-key"
- Vérifier que les keys sont du testnet (pas production)
- Vérifier que `use_testnet=true` dans ExchangeConfig

### Erreur: "Signature for this request is not valid"
- Vérifier timestamp (doit être < 60s de décalage)
- Vérifier que api_secret est correct
- Voir `BinanceBroker._sign_request()` pour debug

### Erreur: "Filter failure: MIN_NOTIONAL"
- Montant trop petit pour l'exchange
- Vérifier `symbol_info.min_notional`

### Balance USDT = 0
- Reset testnet récent (se produit ~1x/mois)
- Se reconnecter sur https://testnet.binance.vision pour réinitialiser

---

## 📚 Références

- **Testnet Binance:** https://testnet.binance.vision
- **API Doc Officielle:** https://binance-docs.github.io/apidocs/spot/en/
- **Notre Implémentation:** `backend/app/brokers/binance_broker.py`
- **Factory Pattern:** `backend/app/brokers/factory.py`
- **ExchangeConfig Model:** `backend/app/models/database_models.py:178`
