# 🔌 GUIDE: INTÉGRATION BROKER RÉEL (Production)

## 📌 Architecture Sécurisée

```
┌─────────────────────────────────────────────────────────┐
│                   CRBOT Application                     │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────┐         ┌──────────────────┐        │
│  │  Risk Manager │────────▶│  Broker Adapter  │        │
│  │  (validate)   │         │  (API calls)     │        │
│  └───────────────┘         └──────────────────┘        │
│                                    │                     │
│  ┌───────────────────────────────────────────────┐     │
│  │  Encryption Layer (API keys chiffrées)        │     │
│  │  - Broker credentials encrypted               │     │
│  │  - Only decrypted at runtime                  │     │
│  │  - Keys in AWS Secrets Manager (prod)         │     │
│  └───────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │    Binance API   │
                    │  (Real Trading)  │
                    └──────────────────┘
```

---

## ✅ STEP 1: Créer un compte Binance (ou autre broker)

### Option A: Binance (Recommandé)
1. Ouvrir https://www.binance.com
2. Sign up avec email
3. Enable 2FA (mandatory en production)
4. Vérifier votre identité (KYC)
5. Configurer withdrawal whitelist

### Option B: MetaTrader
1. Ouvrir MetaTrader 5
2. Créer compte live
3. Dépôt initial
4. Noter login + password + server

---

## 🔐 STEP 2: Créer les API Keys (avec permissions minimales)

### Binance API Keys - Sécurité Maximum

**CREATE API KEY:**
1. Connecté à Binance
2. Aller à: Account → API Management
3. "Create API"
4. Label: "CRBot_Prod"
5. **Enable Restrictions:**
   - ✅ Spot Trading Only (pas futures)
   - ✅ IP Whitelist: [votre IP serveur]
   - ❌ Disable Withdraw
   - ❌ Disable Margin

**Permissions Exactes:**
```
- Trading: ✅ (pour place/cancel orders)
- Margin Trading: ❌ (pas nécessaire)
- Futures Trading: ❌ (risqué)
- Withdrawals: ❌ (prévention theft)
- Account Transfer: ❌
```

**Copy les credentials:**
```
API Key:    xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API Secret: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🔒 STEP 3: Stocker les credentials en sécurité

### Option A: AWS Secrets Manager (Recommandé pour production)
```bash
# Install AWS CLI
pip install boto3

# Create secret
aws secretsmanager create-secret \
  --name crbot/binance/prod \
  --secret-string '{
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET"
  }'

# Dans .env:
USE_AWS_SECRETS_MANAGER=true
AWS_REGION=us-east-1
```

### Option B: HashiCorp Vault
```bash
# Start Vault
vault server -dev

# Store secret
vault kv put secret/crbot/binance \
  api_key="YOUR_API_KEY" \
  api_secret="YOUR_API_SECRET"
```

### Option C: .env (Sécurité Locale)
```
# .env (JAMAIS commiter!)
BINANCE_API_KEY=your_real_api_key
BINANCE_API_SECRET=your_real_api_secret
BINANCE_TESTNET=false
```

---

## 🚀 STEP 4: Intégrer le Broker dans l'application

### Fichier: `backend/app/services/broker/binance_connector.py`

```python
from binance.client import Client
from binance.exceptions import BinanceAPIException
from app.security import key_manager
from app.config import settings
import asyncio

class BinanceConnector:
    """
    Connecteur Binance avec gestion d'erreurs
    """
    
    def __init__(self):
        # Déchiffrer les credentials
        api_key = key_manager.decrypt(settings.BINANCE_API_KEY)
        api_secret = key_manager.decrypt(settings.BINANCE_API_SECRET)
        
        # Testnet ou production?
        self.testnet = settings.BINANCE_TESTNET
        
        # Client Binance
        self.client = Client(
            api_key=api_key,
            api_secret=api_secret,
            testnet=self.testnet
        )
        
        self.mode = "TESTNET" if self.testnet else "REAL TRADING"
    
    def get_account_balance(self) -> dict:
        """Récupère le solde du compte"""
        try:
            account = self.client.get_account()
            return {
                "status": "connected",
                "mode": self.mode,
                "balances": account['balances'],
                "maker_commission": account['makerCommission'],
                "taker_commission": account['takerCommission']
            }
        except BinanceAPIException as e:
            return {"status": "error", "message": str(e)}
    
    def place_order(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        quantity: float,
        price: float,
        stop_loss: float = None,
        take_profit: float = None
    ) -> dict:
        """
        Place une order avec stop-loss et take-profit
        
        Args:
            symbol: e.g., "BTCUSDT"
            side: "BUY" ou "SELL"
            quantity: Nombre de coins
            price: Prix limite
            stop_loss: Prix de stop
            take_profit: Prix de TP
        """
        
        try:
            # 1. Order principale
            main_order = self.client.order_limit(
                symbol=symbol,
                side=side,
                timeInForce='GTC',  # Good-till-cancelled
                quantity=quantity,
                price=price
            )
            
            main_order_id = main_order['orderId']
            
            # 2. Stop-loss order (OCO = One-Cancels-Other)
            if stop_loss and take_profit:
                oco_order = self.client.create_test_order(
                    symbol=symbol,
                    side=("SELL" if side == "BUY" else "BUY"),
                    stopPrice=stop_loss,
                    takeProfit=take_profit,
                    quantity=quantity
                )
                
                return {
                    "status": "success",
                    "main_order_id": main_order_id,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "mode": self.mode
                }
            
            return {
                "status": "success",
                "order_id": main_order_id,
                "mode": self.mode
            }
            
        except BinanceAPIException as e:
            return {
                "status": "error",
                "message": str(e),
                "code": e.status_code
            }
    
    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Annule une order"""
        try:
            result = self.client.cancel_order(
                symbol=symbol,
                orderId=order_id
            )
            return {"status": "success", "cancelled_order": result}
        except BinanceAPIException as e:
            return {"status": "error", "message": str(e)}
    
    def get_order_status(self, symbol: str, order_id: int) -> dict:
        """Récupère le statut d'une order"""
        try:
            order = self.client.get_order(
                symbol=symbol,
                orderId=order_id
            )
            return {
                "status": order['status'],
                "filled": order['executedQty'],
                "remaining": float(order['origQty']) - float(order['executedQty'])
            }
        except BinanceAPIException as e:
            return {"status": "error", "message": str(e)}

# Instance globale
broker_connector = BinanceConnector()
```

---

## 🧪 STEP 5: Tester en TESTNET d'abord

```bash
# Dans .env
BINANCE_TESTNET=true

# Testnet endpoint
# https://testnet.binance.vision (test avec argent fake)

# Test les endpoints
curl http://localhost:8002/api/broker/balance
curl http://localhost:8002/api/broker/test-order
```

---

## 🔄 STEP 6: Migration TESTNET → PRODUCTION

```bash
# AVANT:
BINANCE_TESTNET=true
BINANCE_API_KEY=testnet_key

# APRÈS:
BINANCE_TESTNET=false
BINANCE_API_KEY=production_key  # Credentials réels
```

**Checklist Migration:**
- [ ] Tous les tests passent avec testnet
- [ ] Paper trading 30 jours minimum
- [ ] Risk management parameters finalisés
- [ ] Monitoring setup
- [ ] Backup setup
- [ ] Kill switches activés
- [ ] Starting capital très petit (0.1 BTC / 10 USDT)

---

## 📊 Endpoints Broker

```
GET /api/broker/ping              → Teste connexion
GET /api/broker/balance           → Solde du compte
GET /api/broker/positions         → Positions ouvertes
POST /api/broker/order/create     → Place une order
POST /api/broker/order/cancel     → Annule une order
GET /api/broker/order/{id}        → Statut d'une order
GET /api/broker/account/info      → Info compte
```

---

## 🚨 Sécurité Critique

| ✅ À FAIRE | ❌ À ÉVITER |
|-----------|-----------|
| API keys chiffrées | API keys en plain text |
| IP whitelist Binance | IP whitelist disabled |
| 2FA activé | Pas de 2FA |
| Withdrawal disabled | Withdrawal enabled |
| Spot trading only | Futures/margin enabled |
| Small starting capital | Large starting capital |
| Kill switches | Pas de kill switches |
| 24/7 monitoring | Pas de monitoring |

---

## 🆘 Troubleshooting

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Invalid API Key" | Credentials faux | Vérifier API key/secret |
| "Unauthorized" | IP not whitelisted | Ajouter IP serveur à Binance |
| "Insufficient balance" | Pas assez de fonds | Dépôt supplémentaire |
| "Order qty below minimum" | Quantité trop petite | Vérifier MIN_NOTIONAL |
| "Rate limit exceeded" | Trop d'appels | Ajouter retry logic avec backoff |

---

## 📈 Performance Production

**Métriques à monitorer:**

```
- Latency: <500ms (Binance)
- Win rate: >45%
- Profit factor: >1.5
- Max drawdown: <10%
- Sharpe ratio: >1.0
- Slippage: <0.1%
```

**Si dégradation:**
1. Vérifier logs
2. Vérifier latency réseau
3. Réduire taille position
4. Arrêter trading (STOP button)
5. Analyser la cause

---

Créé: 2025-12-08
