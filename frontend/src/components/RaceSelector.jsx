// components/RaceSelector.jsx
import React, { useRef, useEffect } from "react";
import styles from "./RaceSelector.module.css";

export default function RaceSelector({ schedule, selectedRound, onSelect }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!scrollRef.current) return;
    const active = scrollRef.current.querySelector("[data-active='true']");
    if (active) active.scrollIntoView({ inline: "center", behavior: "smooth" });
  }, [selectedRound]);

  if (!schedule?.rounds?.length) return null;

  return (
    <div className={styles.wrapper}>
      <div className={styles.track} ref={scrollRef}>
        {schedule.rounds.map(r => {
          const active = r.RoundNumber === selectedRound;
          return (
            <button
              key={r.RoundNumber}
              data-active={active}
              className={active ? styles.chipActive : styles.chip}
              onClick={() => onSelect(r.RoundNumber)}
            >
              <span className={styles.rnd}>R{r.RoundNumber}</span>
              <span className={styles.name}>{r.Country}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
