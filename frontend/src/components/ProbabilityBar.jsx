// components/ProbabilityBar.jsx
import React from "react";
import styles from "./ProbabilityBar.module.css";

const TEAM_COLORS = {
  "Red Bull Racing":  "#3671C6",
  "Ferrari":          "#E8002D",
  "Mercedes":         "#27F4D2",
  "McLaren":          "#FF8000",
  "Aston Martin":     "#229971",
  "Alpine":           "#FF87BC",
  "Williams":         "#64C4FF",
  "RB":               "#6692FF",
  "Haas F1 Team":     "#B6BABD",
  "Kick Sauber":      "#52E252",
};

function getTeamColor(name) {
  for (const [key, color] of Object.entries(TEAM_COLORS)) {
    if (name?.includes(key.split(" ")[0])) return color;
  }
  return "#888";
}

export default function ProbabilityBar({ driver, rank }) {
  const color = getTeamColor(driver.team);
  const pct   = Math.min(driver.winProbability, 60); // cap bar at 60% for visual clarity

  return (
    <div className={styles.row}>
      <span className={styles.rank}>{rank}</span>
      <span className={styles.driver}>{driver.driver}</span>
      <div className={styles.barWrap}>
        <div
          className={styles.bar}
          style={{ width: `${(pct / 60) * 100}%`, background: color }}
        />
      </div>
      <span className={styles.pct} style={{ color }}>{driver.winProbability.toFixed(1)}%</span>
    </div>
  );
}
