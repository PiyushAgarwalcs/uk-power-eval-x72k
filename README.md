# UK Wind Forecast Evaluation

Web app that helps a UK utility's day-ahead power buying team (1) see the latest wind
forecast available at decision time and (2) quantify forecast error (MAE, RMSE, bias, WAPE, P90 buffer).
Data: Elexon BMRS FUELHH (actual wind) and WINDFOR (wind forecast), January 2026.

## Live app
- Frontend: https://uk-power-eval-x72k.vercel.app
- Backend API docs: https://uk-power-eval-x72k.onrender.com/docs
- Video demo: https://www.youtube.com/watch?v=wTo4ZOnnIfs

## Repository structure
- `backend/main.py` - FastAPI app and endpoints
- `backend/elexon.py` - Elexon API ingestion, chunking, disk cache
- `backend/analysis.py` - forecast selection and error metrics
- `backend/tests/` - pytest unit tests
- `backend/data/` - cached January 2026 data (gzipped CSV)
- `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`
- `frontend/src/App.js` - dashboard UI; `frontend/src/index.css` - styles

## Run locally
```bash
docker compose up --build
```
Frontend: http://localhost:3000 - Backend: http://localhost:8000/docs

Without Docker: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload`,
then `cd frontend && npm install && npm start`.

## Method and assumptions
- Day-ahead decisions are made on D-1. For each target half-hour the app uses the latest
  forecast published on or before a configurable cutoff on D-1 (default 09:00 UTC).
- Error = forecast − actual. Positive means wind was over-forecast.
- January 2026 is GMT, so UTC equals UK local time.
- January data is cached in the repo, so the deployed app does not call Elexon at runtime.

## AI tool usage
This project was built with the assistance of Claude (Anthropic) for planning, code
generation and review. I reviewed, tested and understand all code submitted.
