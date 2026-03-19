import sys
import os
import logging
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

XGB_PATH  = MODEL_DIR / "xgb_model.pkl"
LGB_PATH  = MODEL_DIR / "lgb_model.pkl"
META_PATH = MODEL_DIR / "model_meta.pkl"



def _make_xgb(scale_pos_weight: float) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",          
        random_state=42,
        n_jobs=-1,
    )


def _make_lgb(scale_pos_weight: float) -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )



def train(X: np.ndarray, y: np.ndarray, feature_names: list):

    neg = (y == 0).sum()
    pos = (y == 1).sum()

    if pos == 0:
        raise ValueError(
            f"No positive samples (wins) found in training data. "
            f"Total rows: {len(y)}. Check that Position column is loading correctly."
        )

    spw = neg / pos
    logger.info(f"Training on {len(y)} samples | wins={pos} | scale_pos_weight={spw:.1f}")

    xgb_model = _make_xgb(spw)
    lgb_model  = _make_lgb(spw)

    
    n_splits = 3 if len(y) < 300 else 5
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    xgb_auc = cross_val_score(xgb_model, X, y, cv=cv, scoring="roc_auc").mean()
    lgb_auc = cross_val_score(lgb_model,  X, y, cv=cv, scoring="roc_auc").mean()
    logger.info(f"CV ROC-AUC → XGB: {xgb_auc:.4f} | LGB: {lgb_auc:.4f}")

    
    xgb_model.fit(X, y)
    lgb_model.fit(X, y)

    joblib.dump(xgb_model, XGB_PATH)
    joblib.dump(lgb_model,  LGB_PATH)
    joblib.dump({
        "features": feature_names,
        "xgb_auc":  float(xgb_auc),
        "lgb_auc":  float(lgb_auc),
    }, META_PATH)

    logger.info("Models saved to %s", MODEL_DIR)
    return {
        "xgb_auc":   round(float(xgb_auc), 4),
        "lgb_auc":   round(float(lgb_auc),  4),
        "n_samples": int(len(y)),
        "n_wins":    int(pos),
    }



def load_models():
    
    if not XGB_PATH.exists():
        raise FileNotFoundError(
            "Models not found. Run first:  python -m src.model train"
        )
    xgb_model = joblib.load(XGB_PATH)
    lgb_model  = joblib.load(LGB_PATH)
    meta       = joblib.load(META_PATH)
    return xgb_model, lgb_model, meta


def predict_race(df_drivers: pd.DataFrame, feature_names: list):
    
    xgb_model, lgb_model, meta = load_models()

    expected  = meta["features"]
    available = [f for f in expected if f in df_drivers.columns]

    if not available:
        raise ValueError("None of the expected features are present in the input DataFrame")

    X = df_drivers[available].fillna(0).values

    p_xgb = xgb_model.predict_proba(X)[:, 1]
    p_lgb = lgb_model.predict_proba(X)[:, 1]

    
    w_xgb = meta.get("xgb_auc", 0.5)
    w_lgb = meta.get("lgb_auc", 0.5)
    total = w_xgb + w_lgb
    p_ensemble = (w_xgb * p_xgb + w_lgb * p_lgb) / total

    
    p_sum = p_ensemble.sum()
    p_norm = p_ensemble / p_sum if p_sum > 0 else p_ensemble

    result = df_drivers[["Driver"]].copy().reset_index(drop=True)
    result["WinProbability"] = (p_norm * 100).round(2)
    result["XGB_Prob"]       = (p_xgb  * 100).round(2)
    result["LGB_Prob"]       = (p_lgb  * 100).round(2)
    result = result.sort_values("WinProbability", ascending=False).reset_index(drop=True)
    result["PredictedPosition"] = result.index + 1

    importances = dict(zip(available, xgb_model.feature_importances_.round(4)))
    return result, importances



def _cli_train():
    from src.data_loader import build_race_dataset
    from src.feature_builder import build_features, get_feature_matrix

    logger.info("Loading data for 2022–2024 ...")
    raw = build_race_dataset([2018, 2019, 2020, 2021, 2022, 2023, 2024])

    logger.info("Raw dataset: %d rows, %d cols", *raw.shape)
    logger.info("Position sample:\n%s", raw["Position"].value_counts().head(10))

    df = build_features(raw)
    logger.info("After feature engineering: %d rows | Won col sum=%d", len(df), df["Won"].sum() if "Won" in df.columns else -1)

    X, y, feats, _ = get_feature_matrix(df)
    metrics = train(X, y, feats)
    print("\nTraining complete:", metrics)


def _cli_predict(year: int, round_number: int):
    from src.data_loader import load_qualifying_times, load_practice_avg
    from src.feature_builder import add_quali_gap, add_grid_normalized

    logger.info(f"Building prediction for {year} R{round_number} ...")

    quali = load_qualifying_times(year, round_number)
    fp1   = load_practice_avg(year, round_number, "FP1")

    if quali.empty:
        print("No qualifying data available for this race yet.")
        return

    df = quali.copy()
    df["GridPosition"] = range(1, len(df) + 1)
    if not fp1.empty:
        df = df.merge(fp1, on="Driver", how="left")

    for col in ["TrackTemp", "AirTemp", "Humidity", "Rainfall",
                "DriverRollingFinish", "TeamRollingFinish", "CircuitAvgFinish"]:
        if col not in df.columns:
            df[col] = float("nan")

    df = add_quali_gap(df)
    df = add_grid_normalized(df)

    meta = joblib.load(META_PATH)
    result, importances = predict_race(df, meta["features"])

    print(f"\n🏁  Predicted winner probabilities — {year} Round {round_number}\n")
    print(result[["PredictedPosition", "Driver", "WinProbability"]].to_string(index=False))
    print("\nTop feature importances:", dict(list(importances.items())[:5]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "train"

    if cmd == "train":
        _cli_train()
    elif cmd == "predict":
        year_   = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
        round_  = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        _cli_predict(year_, round_)
    else:
        print("Usage: python -m src.model [train | predict <year> <round>]")
