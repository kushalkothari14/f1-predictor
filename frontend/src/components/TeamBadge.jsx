// components/TeamBadge.jsx
import React from "react";

const TEAM_COLORS = {
  "Red Bull":    "#3671C6",
  "Ferrari":     "#E8002D",
  "Mercedes":    "#27F4D2",
  "McLaren":     "#FF8000",
  "Aston":       "#229971",
  "Alpine":      "#FF87BC",
  "Williams":    "#64C4FF",
  "RB":          "#6692FF",
  "Haas":        "#B6BABD",
  "Sauber":      "#52E252",
  "Kick":        "#52E252",
};

function getColor(name) {
  if (!name) return "#5a6675";
  for (const [key, color] of Object.entries(TEAM_COLORS)) {
    if (name.includes(key)) return color;
  }
  return "#5a6675";
}

export default function TeamBadge({ name }) {
  const color = getColor(name);
  const short = name?.split(" ").slice(0, 2).join(" ") || "—";
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: "0.35rem",
      fontSize: "0.78rem",
      fontFamily: "var(--font-head)",
      fontWeight: 600,
      letterSpacing: "0.05em",
      color: "var(--muted)",
      textTransform: "uppercase",
    }}>
      <span style={{
        display: "inline-block",
        width: 3,
        height: 14,
        background: color,
        borderRadius: 1,
        flexShrink: 0,
      }} />
      {short}
    </span>
  );
}
