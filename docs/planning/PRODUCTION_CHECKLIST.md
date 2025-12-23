# ============================================
# PRODUCTION READINESS CHECKLIST
# À compléter avant chaque déploiement
# ============================================

## 📋 PRÉ-DÉPLOIEMENT

### Configuration Sécurité
- [ ] `SECRET_KEY` changé (non "dev-insecure-key-change-in-production")
- [ ] `API_KEY_ENCRYPTION_KEY` changé
- [ ] `.env` fichier JAMAIS commité (ajouter à `.gitignore`)
- [ ] Environment variables sécurisées (AWS Secrets Manager, Vault, etc.)
- [ ] HTTPS/TLS activé sur tous les endpoints
- [ ] CORS configuré pour domaines spécifiques uniquement (pas "*")
- [ ] DEBUG=false
- [ ] ENV=production

### Broker & Credentials
- [ ] API keys du broker stockées dans un vault (pas en plain text)
- [ ] Encryption des credentials en base de données
- [ ] BINANCE_TESTNET=false vérifié (si passage aux données réelles)
- [ ] Rate limiting activé sur broker API
- [ ] Authentification 2FA activée sur compte broker
- [ ] API keys du broker ont permissions minimales seulement
- [ ] IP whitelisting activé sur broker (si disponible)

### Base de Données
- [ ] Migration vers PostgreSQL (production)
  ```bash
  DATABASE_URL=postgresql://user:password@hostname:5432/crbot_prod
  ```
- [ ] Backup automatique activé
- [ ] Backup schedule: minimum quotidien
- [ ] Backup rétention: 30 jours minimum
- [ ] Connection pooling configuré
- [ ] SSL connection forcé (PostgreSQL)
- [ ] User database a permissions restrictives
- [ ] Database password fort (20+ caractères, random)

### Cache (Redis)
- [ ] Redis configuré avec password fort
- [ ] Redis persistence activé (RDB/AOF)
- [ ] Redis backup automatique
- [ ] Firewall restreint à IP application uniquement
- [ ] Redis SSL/TLS activé

### Monitoring & Logging
- [ ] LOG_LEVEL=INFO (pas DEBUG)
- [ ] Logs centralisés (ELK, CloudWatch, etc.)
- [ ] Sentry activé pour error tracking
- [ ] Alertes configurées pour:
  - [ ] Erreurs de trading
  - [ ] Déconnexions broker
  - [ ] Drawdown excessif
  - [ ] Position non-clôturée après 24h
  - [ ] Erreurs systèmes

### Risk Management
- [ ] MAX_DAILY_LOSS_PERCENT configuré et testé
- [ ] MAX_DRAWDOWN_PERCENT configuré et testé
- [ ] MAX_TRADES_PER_DAY configuré
- [ ] MAX_POSITION_SIZE_PERCENT configuré
- [ ] Stop-loss obligatoire sur TOUS les trades
- [ ] Take-profit défini ou trailing stop activé
- [ ] Circuit breakers testés en production

### Infrastructure
- [ ] Serveur production (AWS, GCP, Azure, VPS, etc.)
  ```
  Specs recommandées:
  - CPU: 4+ cores
  - RAM: 8GB minimum
  - Storage: 100GB minimum
  - Network: 100Mbps minimum
  ```
- [ ] Load balancing configuré (si multi-instance)
- [ ] SSL/TLS certificate valide (not self-signed)
- [ ] Firewall configuré (ports 443 uniquement pour HTTPS)
- [ ] IP whitelisting activé (si applicable)
- [ ] SSH keys asymétriques (pas de password SSH)
- [ ] Fail-over/redundancy configuré

### Déploiement
- [ ] Docker images optimisées
  ```bash
  # Multi-stage builds
  # Base image minimal (python:3.11-slim)
  # 0 root container access
  ```
- [ ] Docker secrets pour credentials (pas d'env vars)
- [ ] Kubernetes manifests si applicable
- [ ] CI/CD pipeline configuré (GitHub Actions, GitLab CI, etc.)
- [ ] Rollback plan documenté
- [ ] Database migrations tested et documented
- [ ] Staging environment déploiement d'abord

### Tests
- [ ] Unit tests: 80%+ coverage
- [ ] Integration tests: broker API mock + DB
- [ ] Load testing: 1000+ req/sec minimum
- [ ] Stress testing: crash recovery
- [ ] Smoke tests: production endpoints
- [ ] Canary deployment: 5% traffic d'abord

### Backup & Recovery
- [ ] Database backup: quotidien
  ```
  Stratégie:
  - Daily: 7 jours rétention
  - Weekly: 4 semaines
  - Monthly: 12 mois
  ```
- [ ] Backup encryption activé
- [ ] Restore test: hebdomadaire
- [ ] WAL (Write-Ahead Logging) activé PostgreSQL
- [ ] Point-in-time recovery testée

### Notifications
- [ ] Email alerts configuré
- [ ] Discord webhooks configuré
- [ ] Alertes de trading activées
- [ ] Alertes d'erreur système activées
- [ ] Alertes de sécurité activées

### Conformité & Audit
- [ ] Audit log de toutes les trades
- [ ] Audit log des changements de config
- [ ] Audit log des accès API
- [ ] Retention: minimum 7 ans (légal)
- [ ] GDPR compliant (si EU users)
- [ ] Terms of Service documentés
- [ ] Privacy Policy documentée
- [ ] Disclaimer crypto risks affiché

### Documentation
- [ ] Runbook produit (how-to-run)
- [ ] Incident response plan
- [ ] Disaster recovery plan
- [ ] Architecture diagram
- [ ] API documentation complète
- [ ] Configuration reference
- [ ] Troubleshooting guide

---

## 🚨 PRÉ-TRADING (DONNÉES RÉELLES)

### Vérifications Finales
- [ ] Paper trading 1 mois minimum
  ```
  Métriques requises:
  - Win rate > 45%
  - Profit factor > 1.5
  - Max drawdown < 10%
  - Sharpe ratio > 1.0
  ```
- [ ] Tous les tests en production PASSED
- [ ] Latence broker API acceptable (<500ms)
- [ ] Reconnection logic testé
- [ ] Partial fill handling tested
- [ ] Order rejection handling tested
- [ ] Market gap handling tested

### Dégradation Progressive
- [ ] Start small: 0.1 BTC / 10 USDT position size
- [ ] Monitor 24/7 les premières 2 semaines
- [ ] Augmenter la taille graduellement (10% par semaine)
- [ ] Total capital risqué: <1% per trade

### Kill Switches
- [ ] Bouton STOP manual toujours disponible
- [ ] Drawdown circuit breaker: -10% = STOP
- [ ] Daily loss circuit breaker: -5% = STOP
- [ ] Broker connection lost > 5min = STOP
- [ ] API rate limit triggered = STOP

---

## ✅ POST-DÉPLOIEMENT

### J+0 (Launch Day)
- [ ] Monitor logs chaque heure
- [ ] Check broker connection status
- [ ] Verify trades executing correctly
- [ ] Monitor P&L
- [ ] Check database writes
- [ ] Backup successful

### J+1 à J+7 (First Week)
- [ ] Daily monitoring 24/7
- [ ] Performance metrics analysés
- [ ] Logs reviewed pour anomalies
- [ ] Performance vs paper trading comparison
- [ ] User feedback gathered

### J+8 à J+30 (First Month)
- [ ] Weekly performance review
- [ ] Weekly backup verification
- [ ] Security audit
- [ ] Cost analysis
- [ ] Risk metrics reviewed

---

## 📊 COMMANDS DE VÉRIFICATION

```bash
# Vérifier la config prod
curl http://localhost:8002/api/health

# Vérifier la sécurité
echo $SECRET_KEY  # Doit être long et random
echo $ENV         # Doit être "production"

# Vérifier la DB
psql -U crbot -d crbot_prod -c "SELECT COUNT(*) FROM trades;"

# Vérifier les logs
tail -f /var/log/crbot/production.log

# Vérifier l'uptime
uptime

# Vérifier la connexion broker
curl http://localhost:8002/api/broker/ping
```

---

## 🚨 CONTACTS D'URGENCE

Ajouter:
- Broker support contact
- Infrastructure provider contact
- Database admin contact
- Security contact
- Backup admin contact

---

**Version**: 1.0.0  
**Dernière mise à jour**: 2025-12-08  
**Créé par**: CRBot Team
