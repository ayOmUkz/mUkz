"use client";

import { AXIS_GLYPH, AXIS_ORDER, type ForceScores } from "@/lib/types";

interface Props {
  scores: ForceScores;
  size?: number;
}

const RING_LEVELS = [2, 4, 6, 8, 10];
const RADAR_PADDING = 56; // room for axis labels + sign badges

export function GreekRadar({ scores, size = 480 }: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - RADAR_PADDING;
  const angleStep = (2 * Math.PI) / AXIS_ORDER.length;
  // Start at top (-90°) so Δ is straight up
  const startAngle = -Math.PI / 2;

  const pointFor = (axisIndex: number, magnitude: number) => {
    const angle = startAngle + angleStep * axisIndex;
    const r = (magnitude / 10) * radius;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  const axisEnd = (axisIndex: number) => pointFor(axisIndex, 10);

  const polygonPoints = AXIS_ORDER.map((axis, i) => {
    const score = scores[axis];
    const p = pointFor(i, score.magnitude);
    return `${p.x},${p.y}`;
  }).join(" ");

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-label="Greek Radar"
      role="img"
    >
      <defs>
        <radialGradient id="radarGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgb(56, 189, 248)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="rgb(56, 189, 248)" stopOpacity="0.08" />
        </radialGradient>
      </defs>

      {/* Concentric rings */}
      {RING_LEVELS.map((level) => {
        const r = (level / 10) * radius;
        return (
          <circle
            key={level}
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke="rgba(148, 163, 184, 0.15)"
            strokeWidth={1}
          />
        );
      })}

      {/* Spokes */}
      {AXIS_ORDER.map((_, i) => {
        const end = axisEnd(i);
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={end.x}
            y2={end.y}
            stroke="rgba(148, 163, 184, 0.2)"
            strokeWidth={1}
          />
        );
      })}

      {/* Filled polygon for the position */}
      <polygon
        points={polygonPoints}
        fill="url(#radarGlow)"
        stroke="rgb(56, 189, 248)"
        strokeWidth={2}
      />

      {/* Score dots */}
      {AXIS_ORDER.map((axis, i) => {
        const p = pointFor(i, scores[axis].magnitude);
        return (
          <circle
            key={`${axis}-dot`}
            cx={p.x}
            cy={p.y}
            r={4}
            fill="rgb(56, 189, 248)"
          />
        );
      })}

      {/* Axis labels with sign badges */}
      {AXIS_ORDER.map((axis, i) => {
        const labelPos = pointFor(i, 11.4); // outside the outermost ring
        const score = scores[axis];
        const sign = score.sign;
        const signColor =
          sign === "+"
            ? "rgb(34, 197, 94)"
            : sign === "-"
            ? "rgb(239, 68, 68)"
            : "rgba(148, 163, 184, 0.7)";
        return (
          <g key={`${axis}-label`} transform={`translate(${labelPos.x}, ${labelPos.y})`}>
            <text
              textAnchor="middle"
              dominantBaseline="middle"
              fill="rgb(226, 232, 240)"
              fontSize={16}
              fontWeight={600}
              fontFamily="ui-monospace, monospace"
            >
              {AXIS_GLYPH[axis]}
            </text>
            {sign && (
              <text
                textAnchor="middle"
                dominantBaseline="middle"
                y={16}
                fill={signColor}
                fontSize={12}
                fontWeight={700}
                fontFamily="ui-monospace, monospace"
              >
                {sign}
              </text>
            )}
            <text
              textAnchor="middle"
              dominantBaseline="middle"
              y={sign ? 30 : 16}
              fill="rgba(148, 163, 184, 0.8)"
              fontSize={11}
              fontFamily="ui-monospace, monospace"
            >
              {score.magnitude.toFixed(1)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
