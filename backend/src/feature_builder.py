import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


ROLLING_WINDOW = 5          
MISSING_QUALI_GAP = 3.0    
MISSING_GRID = 10.0        
MISSING_FINISH = 10.0      

TEAM_STRENGTH = {
    "Red Bull Racing": 1, "Ferrari": 2, "Mercedes": 3,
    "McLaren": 4, "Aston Martin": 5, "Alpine": 6,
    "Williams": 9, "RB": 7, "Haas F1 Team": 8, "Kick Sauber": 10,
}

def add_team_strength(df):
    df = df.copy()
    df["TeamStrength"] = df["TeamName"].map(
        lambda t: next((v for k, v in TEAM_STRENGTH.items() if isinstance(t, str) and k.split()[0] in t), 7)
    )
    return df

def add_rolling_form(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["Driver", "Year", "Round"]).copy()
    df["Position"] = pd.to_numeric(df["Position"], errors="coerce")

    df["DriverRollingFinish"] = (
        df.groupby("Driver")["Position"]
        .transform(lambda x: x.shift(1).rolling(ROLLING_WINDOW, min_periods=1).mean())
    )
    
    df["DriverRollingFinish"] = df["DriverRollingFinish"].fillna(MISSING_FINISH)
    return df


def add_constructor_form(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["TeamName", "Year", "Round"]).copy()
    df["Position"] = pd.to_numeric(df["Position"], errors="coerce")

    df["TeamRollingFinish"] = (
        df.groupby("TeamName")["Position"]
        .transform(lambda x: x.shift(1).rolling(ROLLING_WINDOW, min_periods=1).mean())
    )
    df["TeamRollingFinish"] = df["TeamRollingFinish"].fillna(MISSING_FINISH)
    return df


def add_circuit_history(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["Driver", "Country", "Year", "Round"]).copy()
    df["Position"] = pd.to_numeric(df["Position"], errors="coerce")

    df["CircuitAvgFinish"] = (
        df.groupby(["Driver", "Country"])["Position"]
        .transform(lambda x: x.shift(1).expanding().mean())
    )
    
    if "DriverRollingFinish" in df.columns:
        df["CircuitAvgFinish"] = df["CircuitAvgFinish"].fillna(df["DriverRollingFinish"])
    df["CircuitAvgFinish"] = df["CircuitAvgFinish"].fillna(MISSING_FINISH)
    return df


def add_quali_gap(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "QualiTimeSec" not in df.columns or df["QualiTimeSec"].isna().all():
        df["QualiGap"] = MISSING_QUALI_GAP
        return df

    if "Year" in df.columns and "Round" in df.columns:
        pole_times = (
            df.groupby(["Year", "Round"])["QualiTimeSec"]
            .min()
            .reset_index()
            .rename(columns={"QualiTimeSec": "PoleTime"})
        )
        df = df.merge(pole_times, on=["Year", "Round"], how="left")
    else:
        df["PoleTime"] = df["QualiTimeSec"].min()

    df["QualiGap"] = (df["QualiTimeSec"] - df["PoleTime"]).clip(0, 10)
    df["QualiGap"] = df["QualiGap"].fillna(MISSING_QUALI_GAP)
    df.drop(columns=["PoleTime"], inplace=True)
    return df

def add_grid_normalized(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["GridPosition"] = pd.to_numeric(df["GridPosition"], errors="coerce")
    df["GridPosition"] = df["GridPosition"].fillna(MISSING_GRID)

    if "Year" in df.columns and "Round" in df.columns:
        max_grid = df.groupby(["Year", "Round"])["GridPosition"].transform("max")
    else:
        max_grid = max(df["GridPosition"].max(), 2)  # plain number, no .clip()

    df["GridNorm"] = 1 - ((df["GridPosition"] - 1) / (np.maximum(max_grid - 1, 1)))
    df["GridNorm"] = df["GridNorm"].fillna(0.5)
    return df


def add_target(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Won"] = (pd.to_numeric(df["Position"], errors="coerce") == 1).astype(int)
    return df



FEATURE_COLS = [
    "GridPosition",
    "GridNorm",
    "QualiGap",
    "DriverRollingFinish",
    "TeamRollingFinish",
    "CircuitAvgFinish",
    "TeamStrength",
    "TrackTemp",
    "AirTemp",
    "Humidity",
    "Rainfall",
]

TARGET_COL = "Won"


def build_features(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        logger.warning("build_features received empty DataFrame")
        return raw_df

    df = raw_df.copy()

    
    df["GridPosition"] = pd.to_numeric(df["GridPosition"], errors="coerce").fillna(MISSING_GRID)
    df["Position"] = pd.to_numeric(df["Position"], errors="coerce")
    df["Position"] = df["Position"].fillna(20) 

    
    df = df[df["Position"].notna()].copy()
    if df.empty:
        logger.warning("No rows with valid Position data")
        return df

    
    weather_defaults = {"TrackTemp": 30.0, "AirTemp": 25.0, "Humidity": 50.0, "Rainfall": 0.0}
    for col, default in weather_defaults.items():
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)

    
    df = add_rolling_form(df)
    df = add_constructor_form(df)
    df = add_circuit_history(df)
    df = add_team_strength(df)
    df = add_quali_gap(df)
    df = add_grid_normalized(df)
    df = add_target(df)

    
    for col in FEATURE_COLS:
        if col in df.columns:
            median = df[col].median()
            if pd.isna(median):
                median = 0.0
            df[col] = df[col].fillna(median)

    logger.info(f"build_features output: {df.shape[0]} rows, {df.shape[1]} cols | wins={df['Won'].sum()}")
    return df


def get_feature_matrix(df: pd.DataFrame):
    
    available = [c for c in FEATURE_COLS if c in df.columns]

    if not available:
        raise ValueError("No feature columns found in DataFrame")

    
    df_clean = df[df[TARGET_COL].notna()].copy()

    
    for col in available:
        df_clean[col] = df_clean[col].fillna(df_clean[col].median())

    if df_clean.empty:
        raise ValueError("No valid rows after filtering — check your data_loader output")

    X = df_clean[available].values
    y = df_clean[TARGET_COL].values

    logger.info(f"Feature matrix: {X.shape} | wins={int(y.sum())} | features={available}")
    return X, y, available, df_clean


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from src.data_loader import build_race_dataset
    raw = build_race_dataset([2023, 2024])
    df = build_features(raw)
    X, y, feats, _ = get_feature_matrix(df)
    print(f"Feature matrix: {X.shape}, Wins: {y.sum()}")
    print("Features:", feats)
