# 🔄 DEVOPS & INFRASTRUCTURE PLAN

## 📋 TABLE DES MATIÈRES
1. [Infrastructure Architecture](#infrastructure-architecture)
2. [Local Development Setup](#local-development-setup)
3. [Containerization Strategy](#containerization-strategy)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Monitoring & Observability](#monitoring--observability)
6. [Backup & Disaster Recovery](#backup--disaster-recovery)
7. [Security & Compliance](#security--compliance)
8. [Scaling Strategy](#scaling-strategy)
9. [Deployment Checklist](#deployment-checklist)

---

## 🏗️ INFRASTRUCTURE ARCHITECTURE

### Local Development (docker-compose)
```yaml
Services:
├── FastAPI Backend (Python 3.11)
├── PostgreSQL 15 (DB)
├── Redis (Cache)
├── React Frontend (Node.js)
├── Prometheus (Metrics)
├── Grafana (Dashboards)
└── PostgreSQL pgAdmin (Management)

Volumes:
├── postgres_data (persisted)
├── redis_data (persisted)
└── logs (mounted)

Networks:
└── crbot_network (internal)
```

### Production Architecture (AWS/GCP)
```
┌─────────────────────────────────────┐
│       CloudFlare CDN / DDoS         │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│       Application Load Balancer     │
│     (SSL/TLS, routing)              │
└──────────────┬──────────────────────┘
               │
      ┌────────┼────────┐
      ↓        ↓        ↓
   [Pod 1]  [Pod 2]  [Pod 3]  ← Kubernetes / ECS (auto-scaling)
      │        │        │
      └────────┼────────┘
               │
    ┌──────────┴──────────┐
    ↓                     ↓
PostgreSQL (RDS)    Redis Cluster
Replication          (HA)
    │                     │
    ├─ Read Replicas     ├─ Cluster Mode
    ├─ Automated Backup  ├─ Persistence
    └─ Multi-AZ          └─ Monitoring
```

### Network Security
- **VPC** : Private subnets pour BD/Cache
- **Security Groups** : Restrict inbound (port 443 only)
- **WAF** : Rate limiting, IP filtering
- **Secrets Manager** : API keys, DB passwords chiffré

---

## 💻 LOCAL DEVELOPMENT SETUP

### Prerequisites
```bash
- Docker & Docker Compose 2.0+
- Python 3.11
- Node.js 18+
- Git

# Recommended: VSCode + Docker extension
```

### Setup Steps
```bash
# 1. Clone repo
git clone <repo> && cd CRBot

# 2. Create .env
cat > .env << EOF
# Backend
FASTAPI_ENV=development
DATABASE_URL=postgresql://user:pass@postgres:5432/crbot
REDIS_URL=redis://redis:6379
SECRET_KEY=your-dev-secret-key

# Broker (test credentials)
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx

# Services
COINGECKO_API_KEY=free_tier
TELEGRAM_BOT_TOKEN=xxx

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password
EOF

# 3. Start services
docker-compose up -d

# 4. Init database
docker-compose exec backend python -m alembic upgrade head

# 5. Load seed data (optional)
docker-compose exec backend python scripts/seed_data.py

# 6. Check health
curl http://localhost:8000/api/health
open http://localhost:3000  # Frontend
open http://localhost:3001  # Grafana (admin/admin)
```

### Directory Structure (After Setup)
```
CRBot/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── schemas/
│   │   ├── models/
│   │   ├── services/
│   │   ├── routes/
│   │   ├── middleware/
│   │   └── utils/
│   ├── tests/
│   ├── migrations/  (Alembic)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
├── frontend/
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── PROJECT_SPECIFICATIONS.md
├── DEVOPS_PLAN.md
└── TEST_STRATEGY.md
```

---

## 🐳 CONTAINERIZATION STRATEGY

### Backend Dockerfile
```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim as builder
WORKDIR /build
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile
```dockerfile
# Build stage
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
```

### Docker Compose (Development)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: crbot
      POSTGRES_PASSWORD: devpass
      POSTGRES_DB: crbot_dev
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U crbot"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://crbot:devpass@postgres:5432/crbot_dev
      REDIS_URL: redis://redis:6379
      FASTAPI_ENV: development
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      REACT_APP_API_URL: http://localhost:8000

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    name: crbot_network
```

---

## 🚀 CI/CD PIPELINE

### GitHub Actions Workflow (.github/workflows/deploy.yml)

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  # ===== TESTING =====
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: pip install pytest pytest-cov pytest-asyncio
      - run: |
          cd backend
          pytest tests/ --cov=app --cov-report=xml --cov-report=term
      - uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml
          fail_ci_if_error: true
          required_coverage: 80

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm ci
      - run: npm run lint
      - run: npm run test -- --coverage --watchAll=false

  # ===== SECURITY =====
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # ===== BUILD & PUSH =====
  build:
    needs: [test-backend, test-frontend, security-scan]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v3
      - uses: docker/setup-buildx-action@v2
      - uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v4
        with:
          context: ./backend
          push: true
          tags: ghcr.io/${{ github.repository }}/backend:${{ github.sha }}

  # ===== DEPLOY =====
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    steps:
      - name: Deploy to Staging
        run: |
          echo "Deploying to staging..."
          # kubectl set image deployment/crbot-backend backend=ghcr.io/${{ github.repository }}/backend:${{ github.sha }} -n staging
```

### Pre-Deployment Checklist
- ✅ All unit tests pass (>80% coverage)
- ✅ Integration tests pass
- ✅ Security scan clean (no critical CVE)
- ✅ Load tests pass (1000 req/sec)
- ✅ Code review approval
- ✅ Changelog updated

---

## 📊 MONITORING & OBSERVABILITY

### Prometheus Metrics

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
```

### Key Metrics to Track

**Backend Performance**
- Request latency (p50, p95, p99)
- Request rate (req/sec)
- Error rate (%)
- Cache hit rate (%)
- Trade execution latency (ms)
- Active WebSocket connections

**Database**
- Connection pool usage (%)
- Query latency (ms)
- Slow query count
- Replication lag (ms)
- Disk usage (%)

**Trading**
- Trades per minute
- Profit factor
- Win rate (%)
- Drawdown (%)
- Backtest duration

**Infrastructure**
- CPU usage (%)
- Memory usage (%)
- Disk usage (%)
- Network I/O (Mbps)

### Grafana Dashboards
1. **Infrastructure** : CPU, Memory, Disk, Network
2. **API Performance** : Latency, Errors, Throughput
3. **Trading Metrics** : Trades, PnL, Drawdown
4. **Database** : Connections, Queries, Replication
5. **Alerts** : Active incidents

### Logging Stack (ELK)

```docker-compose
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
  ports:
    - "9200:9200"

logstash:
  image: docker.elastic.co/logstash/logstash:8.0.0
  volumes:
    - ./monitoring/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  ports:
    - "5000:5000"

kibana:
  image: docker.elastic.co/kibana/kibana:8.0.0
  ports:
    - "5601:5601"
```

### Logging Strategy
- **Format** : JSON (parseable)
- **Levels** : DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Retention** : 7 days hot, 30 days cold
- **Indexes** : Daily rotation (app-2025-12-05)

---

## 💾 BACKUP & DISASTER RECOVERY

### Database Backup Strategy

```bash
# Daily automated backup
# crontab -e
0 2 * * * docker-compose exec -T postgres pg_dump -U crbot crbot_prod | gzip > /backups/crbot_$(date +\%Y\%m\%d).sql.gz

# Upload to S3
0 3 * * * aws s3 cp /backups/crbot_*.sql.gz s3://crbot-backups/ --delete

# Retention: 30 days
0 4 * * * find /backups -name "crbot_*.sql.gz" -mtime +30 -delete
```

### Point-in-Time Recovery (PITR)
```bash
# Enable WAL archiving (PostgreSQL)
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://crbot-wal/%f'

# Recovery
restore_command = 'aws s3 cp s3://crbot-wal/%f %p'
recovery_target_timeline = 'latest'
recovery_target_time = '2025-12-05 10:30:00'
```

### RTO & RPO Objectives
- **RTO** (Recovery Time) : 1 hour max
- **RPO** (Recovery Point) : 15 minutes max (WAL archive freq)

### Disaster Recovery Plan
1. **Detection** : Alert if backup fails
2. **Assessment** : Determine extent of damage
3. **Recovery** : Restore from latest backup + WAL
4. **Validation** : Verify data integrity
5. **Notification** : Alert users

---

## 🔐 SECURITY & COMPLIANCE

### API Security
- **HTTPS Only** : Force redirect
- **CORS** : Whitelist domains
- **Rate Limiting** : 1000 req/min per IP
- **JWT Auth** : 24h token expiry
- **CSRF Protection** : Token-based

### Database Security
- **Encryption at Rest** : AWS RDS encryption
- **Encryption in Transit** : SSL connections
- **Least Privilege** : Separate roles (read, write, admin)
- **Audit Logging** : Query logging enabled

### Secrets Management
```bash
# Store in AWS Secrets Manager or GitHub Secrets
# Never commit secrets to repo
# Rotate API keys every 90 days
```

### Compliance
- **GDPR** : User data deletion on request
- **Data Retention** : Keep trades 7 years for audit
- **PCI DSS** : If handling payment cards (not in MVP)

---

## 📈 SCALING STRATEGY

### Horizontal Scaling (More Pods)
```bash
# Kubernetes Deployment
replicas: 3 → auto-scale to 10 based on CPU/Memory
```

### Vertical Scaling (Bigger Pods)
- Increase CPU/Memory limits
- Database connection pool tuning

### Caching Strategy
- **Redis** : Cache market data (5 min TTL)
- **Browser Cache** : Static assets (1 day)
- **CDN** : Frontend assets via CloudFlare

### Database Scaling
- **Read Replicas** : For analytics queries
- **Sharding** : If data > 1TB (future)
- **Connection Pooling** : PgBouncer (300 connections)

---

## ✅ DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] Code reviewed & approved
- [ ] All tests passing (coverage >80%)
- [ ] Security scan clean
- [ ] Load testing passed
- [ ] Changelog updated
- [ ] Database migrations tested
- [ ] Backup taken
- [ ] Rollback plan documented

### Deployment
- [ ] Deploy to staging first
- [ ] Run smoke tests
- [ ] Check monitoring dashboards
- [ ] Canary release (5% traffic)
- [ ] Monitor error rate (<1%)
- [ ] Gradually increase to 100%

### Post-Deployment
- [ ] All health checks passing
- [ ] Database replication OK
- [ ] Cache warming complete
- [ ] Notify stakeholders
- [ ] Document changes in runbook
- [ ] Schedule rollback if needed

### Rollback Plan
```bash
# If issues detected:
1. Revert code to previous commit
2. Revert database schema if needed
3. Clear cache
4. Monitor metrics for 1 hour
5. Post-incident review
```

---

## 📞 SUPPORT CONTACTS

- **Infrastructure** : DevOps team
- **Database** : DBA on-call
- **Security Incidents** : security@company.com
- **Trading Issues** : PM + Risk team

---

**Last Updated** : 2025-12-05  
**Version** : 1.0
