// pages/Dashboard.jsx
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSchedule, usePrediction, useHealth } from "../hooks/useF1Api";
import ProbabilityBar    from "../components/ProbabilityBar";
import PodiumCard        from "../components/PodiumCard";
import FeatureChart      from "../components/FeatureChart";
import RaceSelector      from "../components/RaceSelector";
import TeamBadge         from "../components/TeamBadge";
import styles            from "./Dashboard.module.css";

const CURRENT_YEAR = 2025;

export default function Dashboard() {
  const params  = useParams();
  const navigate = useNavigate();

  const [year,  setYear]  = useState(parseInt(params.year  || CURRENT_YEAR));
  const [round, setRound] = useState(parseInt(params.round || 1));

  const modelsReady            = useHealth();
  const { data: sched }        = useSchedule(year);
  const { data, loading, error } = usePrediction(year, round);

  // keep URL in sync
  useEffect(() => { navigate(`/${year}/${round}`, { replace: true }); }, [year, round]);

  const top3 = data?.predictions?.slice(0, 3) ?? [];
  const rest  = data?.predictions?.slice(3)   ?? [];

  return (
    <div className={styles.page}>

      {/* ── Header ── */}
      <header className={styles.header}>
        <div className={styles.logoBlock}>
          <span className={styles.logoF1}>F1</span>
          <span className={styles.logoText}>GP Predictor</span>
        </div>
        <nav className={styles.nav}>
          {[2022, 2023, 2024, 2025].map(y => (
            <button
              key={y}
              className={y === year ? styles.navActive : styles.navBtn}
              onClick={() => { setYear(y); setRound(1); }}
            >{y}</button>
          ))}
        </nav>
        <div className={styles.modelPill} data-ready={modelsReady}>
          <span className={styles.dot} />
          {modelsReady ? "Models ready" : "Models not trained"}
        </div>
      </header>

      {/* ── Race Selector ── */}
      <RaceSelector
        schedule={sched}
        selectedRound={round}
        onSelect={setRound}
      />

      {/* ── Event Banner ── */}
      {data && (
        <div className={styles.eventBanner}>
          <div>
            <p className={styles.countryLabel}>{data.country}</p>
            <h1 className={styles.eventName}>{data.eventName}</h1>
          </div>
          <div className={styles.aucs}>
            <div className={styles.aucItem}>
              <span className="mono">{(data.modelsAuc.xgb * 100).toFixed(1)}%</span>
              <span className={styles.aucLabel}>XGB ROC-AUC</span>
            </div>
            <div className={styles.aucItem}>
              <span className="mono">{(data.modelsAuc.lgb * 100).toFixed(1)}%</span>
              <span className={styles.aucLabel}>LGB ROC-AUC</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Loading / Error ── */}
      {loading && (
        <div className={styles.stateBox}>
          <div className={styles.spinner} />
          <p>Loading predictions…</p>
        </div>
      )}

      {error && !loading && (
        <div className={styles.errorBox}>
          <span className={styles.errorIcon}>⚠</span>
          <p>{error}</p>
        </div>
      )}

      {/* ── Main Content ── */}
      {data && !loading && (
        <>
          {/* Podium */}
          <section className={styles.podiumSection}>
            <p className="section-label">Predicted podium</p>
            <div className={styles.podium}>
              {top3[1] && <PodiumCard driver={top3[1]} rank={2} />}
              {top3[0] && <PodiumCard driver={top3[0]} rank={1} />}
              {top3[2] && <PodiumCard driver={top3[2]} rank={3} />}
            </div>
          </section>

          <div className={styles.bottomGrid}>
            {/* Full grid probabilities */}
            <section className={styles.card}>
              <p className="section-label">Win probability — full grid</p>
              <div className={styles.probList}>
                {data.predictions.map((d, i) => (
                  <ProbabilityBar key={d.driver} driver={d} rank={i + 1} />
                ))}
              </div>
            </section>

            {/* Right column */}
            <div className={styles.rightCol}>
              {/* Feature importance */}
              <section className={styles.card}>
                <p className="section-label">What drives the prediction</p>
                <FeatureChart importances={data.featureImportances} />
              </section>

              {/* Driver table */}
              <section className={styles.card}>
                <p className="section-label">Grid detail — P4 onward</p>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Pos</th>
                      <th>Driver</th>
                      <th>Team</th>
                      <th>Grid</th>
                      <th>Win %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rest.map((d, i) => (
                      <tr key={d.driver}>
                        <td className={styles.rankCell}>{i + 4}</td>
                        <td><strong>{d.driver}</strong></td>
                        <td><TeamBadge name={d.team} /></td>
                        <td className="mono">{d.gridPosition ?? "—"}</td>
                        <td className="mono">{d.winProbability.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </div>
          </div>
        </>
      )}

      <footer className={styles.footer}>
        Built with FastF1 + XGBoost + LightGBM — for educational use only
      </footer>
    </div>
  );
}
