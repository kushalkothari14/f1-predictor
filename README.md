# 🏎️ F1 GP Winner Predictor — Complete Guide

A full-stack ML application that predicts Formula 1 race winners using FastF1 data,
XGBoost + LightGBM ensemble models, FastAPI backend, and a React dashboard.

---

## 📁 Project Structure

```
f1-predictor/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── data_loader.py       # FastF1 session fetching
│   │   ├── feature_builder.py   # Feature engineering
│   │   └── model.py             # Train, predict, save/load models
│   ├── data/
│   │   └── f1_cache/            # Auto-created: FastF1 cache files
│   ├── models/                  # Auto-created: saved .pkl model files
│   ├── main.py                  # FastAPI app (all API endpoints)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.js
│   │   ├── styles/
│   │   │   └── global.css
│   │   ├── hooks/
│   │   │   └── useF1Api.js      # API calls (schedule, predict, health)
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Main page
│   │   │   └── Dashboard.module.css
│   │   └── components/
│   │       ├── PodiumCard.jsx   # Top 3 visual cards
│   │       ├── PodiumCard.module.css
│   │       ├── ProbabilityBar.jsx  # Coloured bar per driver
│   │       ├── ProbabilityBar.module.css
│   │       ├── FeatureChart.jsx  # Recharts bar chart
│   │       ├── RaceSelector.jsx  # Horizontal round picker
│   │       ├── RaceSelector.module.css
│   │       └── TeamBadge.jsx    # Team colour indicator
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── README.md  ← you are here
```

---

## 🚀 STEP 1 — Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### 1A. Clone / set up the project

```bash
git init f1-predictor
cd f1-predictor
# (copy all files as provided)
```

### 1B. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify FastF1 installed correctly
python -c "import fastf1; print(fastf1.__version__)"
```

### 1C. Train the models (REQUIRED before predictions work)

This downloads ~2-4 GB of FastF1 data over several sessions. Run it once and it caches locally.

```bash
# From the backend/ directory, with venv active:
python -m src.model train
```

Expected output:
```
INFO  Loading 2019 R1 – Australian Grand Prix
INFO  Loading 2019 R2 – Bahrain Grand Prix
...
INFO  Training on 2140 samples | wins=107 | scale_pos_weight=19.0
INFO  CV ROC-AUC → XGB: 0.8431 | LGB: 0.8502
INFO  Models saved.
Training complete: {'xgb_auc': 0.8431, 'lgb_auc': 0.8502, ...}
```

> 💡 **Tip**: To train faster, edit `_cli_train()` in `model.py` and change years to `[2023, 2024]`

### 1D. Test a prediction from CLI

```bash
python -m src.model predict 2025 1
```

### 1E. Start the backend API

```bash
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs — you'll see the full Swagger UI for all endpoints.

### 1F. Start the frontend (new terminal)

```bash
cd frontend
npm install
npm start
```

Open http://localhost:3000 — the dashboard is live!

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Check if models are trained and ready |
| GET | `/api/schedule/{year}` | Full race calendar for a season |
| GET | `/api/predict/{year}/{round}` | Predict winner probabilities for a GP |
| GET | `/api/history/{year}/{round}` | Actual race results (past races) |
| GET | `/api/drivers/{year}` | All drivers for a season |
| POST | `/api/train` | Trigger model retraining (background task) |

**Example predict response:**
```json
{
  "year": 2025,
  "round": 1,
  "eventName": "Australian Grand Prix",
  "country": "Australia",
  "predictions": [
    {
      "position": 1,
      "driver": "VER",
      "team": "Red Bull Racing",
      "winProbability": 34.2,
      "xgbProb": 33.8,
      "lgbProb": 34.6,
      "gridPosition": 1,
      "qualiGap": 0.0
    },
    ...
  ],
  "featureImportances": {
    "GridPosition": 0.31,
    "QualiGap": 0.27,
    "DriverRollingFinish": 0.18,
    ...
  },
  "modelsAuc": { "xgb": 0.8431, "lgb": 0.8502 }
}
```

---

## 🐳 STEP 2 — Docker (Run Everything Together)

### Prerequisites
- Docker Desktop installed and running

```bash
# From project root (f1-predictor/)
docker-compose up --build
```

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000
- Swagger docs → http://localhost:8000/docs

To train models inside Docker:
```bash
docker exec -it f1_backend python -m src.model train
```

---

## ☁️ STEP 3 — Deploy to the Cloud

### Option A: Render.com (Free tier — easiest)

**Backend:**
1. Go to https://render.com → New → Web Service
2. Connect your GitHub repo
3. Settings:
   - Root Directory: `backend`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variable: `PYTHONUNBUFFERED=1`
5. Add a Disk (Render persistent disk) mounted at `/app/data` for cache

**Frontend:**
1. New → Static Site
2. Root Directory: `frontend`
3. Build Command: `npm install && npm run build`
4. Publish Directory: `build`
5. Add environment variable: `REACT_APP_API_URL=https://your-backend.onrender.com/api`

---

### Option B: Railway.app (Simple, $5/month)

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# Deploy backend
cd backend
railway init
railway up

# Deploy frontend
cd ../frontend
railway init
railway up
```

Set env vars via Railway dashboard:
- Backend: `PYTHONUNBUFFERED=1`
- Frontend: `REACT_APP_API_URL=https://your-backend.up.railway.app/api`

---

### Option C: VPS (DigitalOcean / AWS EC2 / Hetzner)

```bash
# On your server:
sudo apt update && sudo apt install -y docker.io docker-compose

# Clone repo
git clone https://github.com/yourusername/f1-predictor.git
cd f1-predictor

# Run
docker-compose up -d

# Train models
docker exec -it f1_backend python -m src.model train
```

Point your domain with a reverse proxy (nginx or Caddy) to ports 3000 and 8000.

---

### Option D: Vercel (Frontend) + Railway (Backend)

This is the recommended combination for production:

**Frontend → Vercel:**
```bash
cd frontend
npm install -g vercel
vercel          # follow prompts
# Set env var REACT_APP_API_URL in Vercel dashboard
```

**Backend → Railway** (see Option B)

---

## 🧠 How the ML Works

```
FastF1 API
    ↓
Session data: Qualifying times, FP1 avg laps, Race results, Weather
    ↓
Feature Engineering:
  - GridPosition         (P1 = most predictive single feature)
  - QualiGap             (gap to pole, in seconds)
  - GridNorm             (normalised grid 0→1)
  - DriverRollingFinish  (rolling avg of last 5 finishes)
  - TeamRollingFinish    (constructor momentum)
  - CircuitAvgFinish     (driver's history at this track)
  - TrackTemp / AirTemp / Humidity / Rainfall
    ↓
XGBoost classifier  ──┐
                       ├─ Weighted ensemble → WinProbability
LightGBM classifier ──┘
    ↓
Normalized probabilities per driver (sums to 100%)
```

**Why ensemble?**
XGBoost and LightGBM have different regularisation approaches — averaging their outputs reduces variance and improves reliability, especially for edge cases like wet races or backmarkers starting from the front.

**Handling class imbalance:**
Only 1 of ~20 drivers wins each race. We use `scale_pos_weight = (n_races × 19) / n_races` to prevent the model from always predicting "did not win".

---

## 🔧 Customisation Ideas

| Idea | How |
|------|-----|
| Add tyre strategy | `session.laps["Compound"]` — encode stint lengths |
| Safety car probability | Historical safety car data by circuit |
| Weather forecast | OpenWeatherMap API → append to features |
| Driver age / experience | Ergast API → `drivers` endpoint |
| Live quali feed | Re-run prediction after each quali session |
| Email alerts | SendGrid API → notify when prediction is ready |
| Historical accuracy tracking | Compare predictions vs actual results |

---

## ❓ Troubleshooting

**"Models not found" error:**
→ Run `python -m src.model train` first.

**FastF1 download is slow:**
→ Normal! First run downloads ~2-4 GB. Subsequent runs use the cache.

**Quali data unavailable for future races:**
→ The predict endpoint returns 404 if qualifying hasn't happened yet. Run after quali Saturday.

**CORS error in browser:**
→ Make sure the backend is running and `REACT_APP_API_URL` points to the correct URL.

**Out of memory during training:**
→ Reduce years: change `range(2019, 2025)` to `range(2022, 2025)` in `_cli_train()`.
