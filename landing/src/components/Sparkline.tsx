import { useSparklineData } from '../hooks/useSparklineData';

interface SparklineProps {
  width?: number;
  height?: number;
  className?: string;
}

/** Mini-gráfico de líneas animado (motivo visual recurrente, decorativo / aria-hidden). */
export function Sparkline({ width = 220, height = 56, className }: SparklineProps) {
  const data = useSparklineData();
  const max = 100;
  const step = width / (data.length - 1);

  const points = data
    .map((value, index) => `${index * step},${height - (value / max) * height}`)
    .join(' ');

  const areaPoints = `0,${height} ${points} ${width},${height}`;

  return (
    <svg
      className={className}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden="true"
      focusable="false"
    >
      <polygon points={areaPoints} fill="url(#sparkline-fill)" opacity={0.25} />
      <polyline
        points={points}
        fill="none"
        stroke="var(--accent)"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <defs>
        <linearGradient id="sparkline-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.6} />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
        </linearGradient>
      </defs>
    </svg>
  );
}
