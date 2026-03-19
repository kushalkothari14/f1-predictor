
import os
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import joblib


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="F1 GP Winner Predictor API",
    description="Predict Formula 1 race winners using FastF1 + ML",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_DIR = Path(__file__).parent / "models"
META_PATH = MODEL_DIR / "model_meta.pkl"


class TrainRequest(BaseModel):
    years: list[int] = list(range(2019, 2025))


class DriverPrediction(BaseModel):
    position: int
    driver: str
    team: str | None
    winProbability: float
    xgbProb: float
    lgbProb: float
    gridPosition: int | None
    qualiGap: float | None


class PredictionResponse(BaseModel):
    year: int
    round: int
    eventName: str
    country: str
    predictions: list[DriverPrediction]
    featureImportances: dict
    modelsAuc: dict



@app.get("/api/health")
async def health():
    models_ready = META_PATH.exists()
    return {"status": "ok", "modelsReady": models_ready}



@app.get("/api/schedule/{year}")
async def get_schedule(year: int):
    try:
        from src.data_loader import get_event_schedule
        sched = get_event_schedule(year)
        if sched.empty:
            raise HTTPException(status_code=404, detail=f"No schedule found for {year}")

        records = sched.to_dict(orient="records")
        # Convert Timestamps to strings
        for r in records:
            for k, v in r.items():
                if hasattr(v, "isoformat"):
                    r[k] = v.isoformat()
        return {"year": year, "rounds": records}
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/predict/{year}/{round_number}")
async def predict(year: int, round_number: int):
    """
    Predict winner probabilities for a given race.
    Works for both upcoming (no results yet) and past races.
    """
    try:
        from src.data_loader import (
            load_qualifying_times, load_practice_avg,
            load_race_results, get_event_schedule,
        )
        from src.feature_builder import add_quali_gap, add_grid_normalized
        from src.model import load_models, predict_race

        
        sched = get_event_schedule(year)
        event_row = sched[sched["RoundNumber"] == round_number]
        event_name = event_row["EventName"].values[0] if not event_row.empty else f"Round {round_number}"
        country    = event_row["Country"].values[0]   if not event_row.empty else "Unknown"

        
        quali = load_qualifying_times(year, round_number)
        fp1   = load_practice_avg(year, round_number, "FP1")

        if quali.empty:
            raise HTTPException(status_code=404, detail="Qualifying data not available yet")

        df = quali.copy()
        df["GridPosition"] = range(1, len(df) + 1)
        if not fp1.empty:
            df = df.merge(fp1, on="Driver", how="left")

        
        results = load_race_results(year, round_number)
        if not results.empty:
            teams = results[["Driver", "TeamName"]].drop_duplicates()
            df = df.merge(teams, on="Driver", how="left")
        else:
            df["TeamName"] = "—"

        
        for col in ["TrackTemp", "AirTemp", "Humidity", "Rainfall",
                    "DriverRollingFinish", "TeamRollingFinish", "CircuitAvgFinish"]:
            if col not in df.columns:
                df[col] = np.nan

        
        from src.feature_builder import add_team_strength
        df = add_team_strength(df)

        df = add_quali_gap(df)
        df = add_grid_normalized(df)

        meta = joblib.load(META_PATH)
        predictions_df, importances = predict_race(df, meta["features"])

        
        if "TeamName" in df.columns:
            predictions_df = predictions_df.merge(df[["Driver", "TeamName", "GridPosition", "QualiGap"]],
                                                   on="Driver", how="left")

        preds = []
        for _, row in predictions_df.iterrows():
            preds.append(DriverPrediction(
                position=int(row["PredictedPosition"]),
                driver=str(row["Driver"]),
                team=str(row.get("TeamName") or "—"),
                winProbability=round(float(row["WinProbability"]), 2),
                xgbProb=round(float(row["XGB_Prob"]), 2),
                lgbProb=round(float(row["LGB_Prob"]), 2),
                gridPosition=int(row["GridPosition"]) if pd.notna(row.get("GridPosition")) else None,
                qualiGap=round(float(row["QualiGap"]), 3) if pd.notna(row.get("QualiGap")) else None,
            ))

        return PredictionResponse(
            year=year,
            round=round_number,
            eventName=str(event_name),
            country=str(country),
            predictions=preds,
            featureImportances={k: float(v) for k, v in importances.items()},
            modelsAuc={
                "xgb": round(float(meta.get("xgb_auc", 0)), 4),
                "lgb": round(float(meta.get("lgb_auc", 0)), 4),
            },
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/history/{year}/{round_number}")
async def get_history(year: int, round_number: int):
    try:
        from src.data_loader import load_race_results
        results = load_race_results(year, round_number)
        if results.empty:
            raise HTTPException(status_code=404, detail="No results found")

        records = results.to_dict(orient="records")
        return {"year": year, "round": round_number, "results": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/drivers/{year}")
async def get_drivers(year: int):
    try:
        from src.data_loader import build_race_dataset
        from src.feature_builder import build_features
        raw = build_race_dataset([year])
        if raw.empty:
            raise HTTPException(status_code=404, detail="No data")
        df = build_features(raw)
        drivers = df[["Driver", "TeamName"]].drop_duplicates().to_dict(orient="records")
        return {"year": year, "drivers": drivers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



_training = False

def _do_train(years: list[int]):
    global _training
    try:
        from src.data_loader import build_race_dataset
        from src.feature_builder import build_features, get_feature_matrix
        from src.model import train

        raw = build_race_dataset(years)
        df  = build_features(raw)
        X, y, feats, _ = get_feature_matrix(df)
        metrics = train(X, y, feats)
        logger.info("Training complete: %s", metrics)
    finally:
        _training = False


@app.post("/api/train")
async def trigger_train(req: TrainRequest, background_tasks: BackgroundTasks):
    global _training
    if _training:
        return {"status": "already_training"}
    _training = True
    background_tasks.add_task(_do_train, req.years)
    return {"status": "training_started", "years": req.years}



@app.get("/")
async def root():
    return {"message": "F1 Predictor API – visit /docs for Swagger UI"}
