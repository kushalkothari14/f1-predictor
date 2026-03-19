// components/PodiumCard.jsx
import React from "react";
import TeamBadge from "./TeamBadge";
import styles from "./PodiumCard.module.css";

const RANK_CONFIG = {
  1: { label: "Winner",  height: 160, glow: "#ffd600" },
  2: { label: "2nd",     height: 120, glow: "#a8b8c8" },
  3: { label: "3rd",     height: 100, glow: "#cd7f32" },
};

export default function PodiumCard({ driver, rank }) {
  const cfg = RANK_CONFIG[rank];
  return (
    <div
      className={styles.card}
      style={{
        "--h": cfg.height + "px",
        "--glow": cfg.glow,
        order: rank === 1 ? 2 : rank === 2 ? 1 : 3,
      }}
    >
      <div className={styles.inner}>
        <div className={styles.rank} style={{ color: cfg.glow }}>P{rank}</div>
        <div className={styles.driver}>{driver.driver}</div>
        <TeamBadge name={driver.team} />
        <div className={styles.prob}>{driver.winProbability.toFixed(1)}%</div>
        <div className={styles.probLabel}>win prob.</div>
        {driver.gridPosition && (
          <div className={styles.grid}>Grid P{driver.gridPosition}</div>
        )}
      </div>
      <div className={styles.podiumStep} />
    </div>
  );
}
