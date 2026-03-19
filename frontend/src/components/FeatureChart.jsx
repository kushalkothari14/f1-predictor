// components/FeatureChart.jsx
import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const FEATURE_LABELS = {
  GridPosition:       "Grid Position",
  GridNorm:           "Grid (norm.)",
  QualiGap:           "Quali Gap (s)",
  DriverRollingFinish: "Driver Form",
  TeamRollingFinish:  "Team Form",
  CircuitAvgFinish:   "Circuit History",
  TrackTemp:          "Track Temp",
  AirTemp:            "Air Temp",
  Humidity:           "Humidity",
  Rainfall:           "Rain",
};

const COLORS = ["#e8001d", "#ff3352", "#ff6b6b", "#ffa07a", "#ffd600", "#a8b8c8", "#7eb8e8", "#60c8a8"];

export default function FeatureChart({ importances }) {
  if (!importances) return null;

  const data = Object.entries(importances)
    .map(([k, v]) => ({ name: FEATURE_LABELS[k] || k, value: parseFloat((v * 100).toFixed(1)) }))
    .sort((a, b) => b.value - a.value);

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: "#5a6675", fontFamily: "Share Tech Mono" }}
          tickFormatter={v => `${v}%`}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={120}
          tick={{ fontSize: 11, fill: "#a8b8c8", fontFamily: "Barlow Condensed" }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={v => [`${v}%`, "Importance"]}
          contentStyle={{
            background: "#0f1318",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 4,
            fontFamily: "Share Tech Mono",
            fontSize: 12,
          }}
          labelStyle={{ color: "#e8edf2" }}
        />
        <Bar dataKey="value" radius={[0, 2, 2, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.8} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
