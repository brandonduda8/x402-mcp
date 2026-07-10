import { useMemo } from "react";
import type { ToolEvent } from "../types/api";

interface RateSparklineProps {
  events: ToolEvent[];
  rateLimit: number;
  density: string;
}

export function RateSparkline({ events, rateLimit, density }: RateSparklineProps) {
  // Bucket events into 1-minute windows for the last 10 minutes
  const buckets = useMemo(() => {
    const now = Date.now();
    const bins = Array(10).fill(0) as number[];
    for (const e of events) {
      if (e.type === "heartbeat") continue;
      const age = now - new Date(e.ts).getTime();
      const bucket = Math.floor(age / 60_000);
      if (bucket >= 0 && bucket < 10) {
        bins[9 - bucket]++;
      }
    }
    return bins;
  }, [events]);

  const max = Math.max(rateLimit, ...buckets);
  const width = 200;
  const height = 50;
  const barW = width / buckets.length - 2;

  return (
    <div className="panel" style={{ gridColumn: "span 4" }}>
      <div className="panel-title">
        Rate (calls/min)
        {density === "guided" && (
          <span
            title="Tool calls per minute over the last 10 minutes. Limit shown as dashed line."
            style={{ cursor: "help", opacity: 0.6 }}
          >
            ?
          </span>
        )}
      </div>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        aria-label="Rate sparkline"
        style={{ display: "block" }}
      >
        {/* Rate limit line */}
        <line
          x1={0}
          y1={height - (rateLimit / max) * height}
          x2={width}
          y2={height - (rateLimit / max) * height}
          stroke="var(--color-amber)"
          strokeWidth={1}
          strokeDasharray="4 2"
          opacity={0.5}
        />
        {/* Bars */}
        {buckets.map((count, i) => {
          const barH = max > 0 ? (count / max) * (height - 4) : 0;
          const isOverLimit = count >= rateLimit;
          return (
            <rect
              key={i}
              x={i * (barW + 2) + 1}
              y={height - barH}
              width={barW}
              height={barH}
              rx={2}
              fill={isOverLimit ? "var(--color-red)" : "var(--color-usdc)"}
              opacity={0.8}
            />
          );
        })}
      </svg>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "11px",
          color: "var(--color-text-muted)",
          marginTop: "4px",
        }}
      >
        <span>10m ago</span>
        <span>now</span>
      </div>
    </div>
  );
}
