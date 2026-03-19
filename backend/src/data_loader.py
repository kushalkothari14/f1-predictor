
import fastf1
import pandas as pd
import numpy as np
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CACHE_DIR = Path(__file__).parent.parent / "data" / "f1_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))



def _safe_load(year: int, round_number: int, session_type: str):
    try:
        session = fastf1.get_session(year, round_number, session_type)
        session.load(laps=True, telemetry=False, weather=True, messages=False)
        return session
    except Exception as e:
        logger.warning(f"Could not load {year} R{round_number} {session_type}: {e}")
        return None

def load_race_results(year: int, round_number: int) -> pd.DataFrame:
    
    session = _safe_load(year, round_number, "R")
    if session is None:
        return pd.DataFrame()

    cols = ["Abbreviation", "TeamName", "GridPosition", "Position", "Points", "Status"]
    df = session.results[cols].copy()
    df.rename(columns={"Abbreviation": "Driver"}, inplace=True)
    df["Year"] = year
    df["Round"] = round_number
    df["EventName"] = session.event["EventName"]
    df["Country"] = session.event["Country"]
    return df


def load_qualifying_times(year: int, round_number: int) -> pd.DataFrame:
    try:
        session = fastf1.get_session(year, round_number, "Q")
        session.load(laps=True, telemetry=False, weather=False, messages=False)

        if session.laps is None or session.laps.empty:
            return pd.DataFrame()

        laps = session.laps.pick_quicklaps()
        if laps.empty:
            return pd.DataFrame()

        best = (
            laps.groupby("Driver")["LapTime"]
            .min()
            .dt.total_seconds()
            .reset_index()
            .rename(columns={"LapTime": "QualiTimeSec"})
        )
        return best
    except Exception as e:
        logger.warning(f"Could not load {year} R{round_number} Q: {e}")
        return pd.DataFrame()


def load_practice_avg(year: int, round_number: int, fp: str = "FP1") -> pd.DataFrame:
    try:
        session = fastf1.get_session(year, round_number, fp)
        session.load(laps=True, telemetry=False, weather=False, messages=False)
        
        if session.laps is None or session.laps.empty:
            return pd.DataFrame()

        laps = session.laps.pick_quicklaps()
        if laps.empty:
            return pd.DataFrame()

        avg = (
            laps.groupby("Driver")["LapTime"]
            .mean()
            .dt.total_seconds()
            .reset_index()
            .rename(columns={"LapTime": f"{fp}_AvgLap"})
        )
        return avg
    except Exception as e:
        logger.warning(f"Could not load {year} R{round_number} {fp}: {e}")
        return pd.DataFrame()


def load_weather_summary(year: int, round_number: int) -> dict:
    
    session = _safe_load(year, round_number, "R")
    if session is None or session.weather_data is None or session.weather_data.empty:
        return {}

    wd = session.weather_data
    return {
        "TrackTemp": wd["TrackTemp"].mean(),
        "AirTemp": wd["AirTemp"].mean(),
        "Humidity": wd["Humidity"].mean(),
        "Rainfall": int(wd["Rainfall"].any()),
    }


def get_event_schedule(year: int) -> pd.DataFrame:
    
    try:
        sched = fastf1.get_event_schedule(year, include_testing=False)
        return sched[["RoundNumber", "EventName", "Country", "EventDate"]]
    except Exception as e:
        logger.warning(f"Could not get schedule for {year}: {e}")
        return pd.DataFrame()



def build_race_dataset(years: list[int]) -> pd.DataFrame:
    
    all_rows = []

    for year in years:
        schedule = get_event_schedule(year)
        if schedule.empty:
            continue

        for _, event in schedule.iterrows():
            rnd = int(event["RoundNumber"])
            logger.info(f"Loading {year} R{rnd} – {event['EventName']}")

            results = load_race_results(year, rnd)
            if results.empty:
                continue

            quali = load_qualifying_times(year, rnd)
            fp1 = load_practice_avg(year, rnd, "FP1")
            weather = load_weather_summary(year, rnd)

            
            df = results.copy()
            if not quali.empty:
                df = df.merge(quali, on="Driver", how="left")
            if not fp1.empty:
                df = df.merge(fp1, on="Driver", how="left")

            
            for k, v in weather.items():
                df[k] = v

            all_rows.append(df)

    if not all_rows:
        return pd.DataFrame()

    combined = pd.concat(all_rows, ignore_index=True)
    logger.info(f"Dataset built: {combined.shape[0]} rows, {combined.shape[1]} columns")
    return combined


if __name__ == "__main__":
    
    df = build_race_dataset([2023, 2024])
    print(df.head())
    print(df.dtypes)
