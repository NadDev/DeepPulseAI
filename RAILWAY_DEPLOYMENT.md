# CRBot Backend - Railway Deployment Guide

## Architecture

```
Frontend (Vercel) → Backend (Railway) → Supabase PostgreSQL
   React                 FastAPI           Database
```

## Prerequisites

1. **Railway Account** - https://railway.app (free tier available)
2. **GitHub Repository** - Connected to Railway
3. **Supabase Project** - Database tables created
4. **Environment Variables** - Configured in Railway

## Step 1: Prepare Supabase

### Create Tables in Supabase

1. Go to https://app.supabase.com/project/opnouxerbecxofzekwpm/sql/new
2. Copy-paste the content of `../database/supabase_schema.sql`
3. Click "Run" (Ctrl+Enter)
4. Wait for all tables to be created

**Note:** If you get foreign key errors on `auth.users`, you can ignore them for now. The RLS policies will work once users register.

### Get Supabase Connection String

1. Go to Supabase Settings → Database → Connection Pooling
2. Copy the **Connection string (URI)** 
3. Replace `[YOUR-PASSWORD]` with your database password
4. Save this - you'll need it for Railway

Example format:
```
postgresql://postgres:PASSWORD@db.opnouxerbecxofzekwpm.supabase.co:5432/postgres
```

## Step 2: Deploy on Railway

### Option A: GitHub Integration (Recommended)

1. **Create Railway Project**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize GitHub
   - Select `NadDev/CRBot` repository

2. **Configure Service**
   - Railway will auto-detect the Dockerfile in `backend/`
   - Set root directory to `backend/` if needed

3. **Add Environment Variables**
   - Click "Variables"
   - Add all variables from `.env`:

   ```
   ENV=production
   SUPABASE_URL=https://opnouxerbecxofzekwpm.supabase.co
   SUPABASE_ANON_KEY=sb_publishable_QKhstCwE2ToLugAu2gVt6w_vVO7a9nR
   SUPABASE_SERVICE_KEY=sb_secret_LQUc2jVhsp359jvcf1UZBg_T4irZzlp
   DATABASE_URL=postgresql://postgres:PASSWORD@db.opnouxerbecxofzekwpm.supabase.co:5432/postgres
   TIMESCALE_HOST=idfffrs9u1.d4bmrstuve.tsdb.cloud.timescale.com
   TIMESCALE_PORT=35095
   TIMESCALE_DATABASE=tsdb
   TIMESCALE_USER=tsdbadmin
   TIMESCALE_PASSWORD=h04aqav18vv5vguc
   TIMESCALE_URL=postgresql://tsdbadmin:PASSWORD@idfffrs9u1.d4bmrstuve.tsdb.cloud.timescale.com:35095/tsdb?sslmode=require
   SECRET_KEY=prod-secret-key-change-me
   API_KEY_ENCRYPTION_KEY=prod-encryption-key-change-me
   ```

4. **Deploy**
   - Push changes to GitHub
   - Railway will auto-deploy
   - Wait 2-3 minutes for build to complete

### Option B: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Deploy
railway up

# View logs
railway logs

# Get service URL
railway status
```

## Step 3: Verify Deployment

1. **Get Backend URL**
   - Go to your Railway project
   - Click the "Backend" service
   - Copy the "Public URL" (e.g., `https://crbot-backend-prod.railway.app`)

2. **Test Health Endpoint**
   ```bash
   curl https://crbot-backend-prod.railway.app/api/health
   ```
   Should return: `{"status": "ok"}`

3. **Test Database Connection**
   ```bash
   curl https://crbot-backend-prod.railway.app/api/portfolio/summary \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

## Step 4: Update Frontend

Update `frontend/.env.production`:

```
VITE_SUPABASE_URL=https://opnouxerbecxofzekwpm.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_QKhstCwE2ToLugAu2gVt6w_vVO7a9nR
VITE_API_URL=https://crbot-backend-prod.railway.app
```

## Step 5: Deploy Frontend on Vercel

1. Go to https://vercel.com
2. Import your GitHub repository
3. Set framework: Next.js (or React)
4. Add environment variables from `.env.production`
5. Deploy

## Monitoring

### View Logs
- Railway Dashboard → Backend → Logs

### Monitor Metrics
- CPU, Memory, Network usage in Railway Dashboard

### Error Tracking
- Check logs for any connection errors
- Verify DATABASE_URL is correct

## Troubleshooting

### "connection refused"
- Check DATABASE_URL is correct
- Verify Supabase firewall allows Railway IP
- Check if tables exist in Supabase

### "relation does not exist"
- Run the schema.sql in Supabase first
- Verify tables were created successfully

### "401 Unauthorized"
- Check SUPABASE keys are correct
- Verify JWT tokens are valid

### Build fails
- Check Docker build locally: `docker build -f backend/Dockerfile -t crbot-backend .`
- Verify all dependencies in requirements.txt

## Costs

**Railway Pricing**
- Free tier: $5/month included
- Pay as you go after
- **Estimated for CRBot**: $5-15/month

**Supabase Pricing**
- Free tier: Up to 500MB database
- Pro: $25/month (1GB database + features)
- **Current usage**: ~2MB (well within free tier)

**Timescale Pricing**
- Performance plan: $30/month
- (Optional: only for high-frequency market data)

## Next Steps

1. ✅ Supabase schema created
2. ✅ Database configured in Railway
3. ⏳ Seed initial data: `python seed_data.py`
4. ⏳ Deploy frontend on Vercel
5. ⏳ Test end-to-end

## Support

- Railway Docs: https://docs.railway.app
- Supabase Docs: https://supabase.com/docs
- FastAPI Docs: https://fastapi.tiangolo.com
