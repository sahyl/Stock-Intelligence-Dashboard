# JarNox Stock Intelligence Dashboard

Beautiful, production-ready internship assignment using **FastAPI + YFinance + Tailwind + Chart.js**.

## Features Implemented
- ✅ FastAPI backend with Swagger docs (`/docs`)
- ✅ Alpha Vantage real data (full history cached in SQLite)
- ✅ All required endpoints + bonus `/compare`
- ✅ Stunning modern frontend (dark glassmorphic UI)
- ✅ Daily Return, 7-day MA, 52-week high/low
- ✅ Custom metric: Volatility Score
- ✅ Compare two stocks with correlation
- ✅ Responsive + mobile-friendly

## Setup (2 minutes)
1. `pip install -r requirements.txt`
2. `cp .env.example .env` and paste your key
3. `uvicorn main:app --reload`
4. Open https://jarnox-stock-intelligence-dashboard.onrender.com


First load may take 30–60 seconds (caches full history for 6 stocks). After that — instant.

Enjoy! 🚀
