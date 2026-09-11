import { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  AlertTriangle,
  Calendar,
  FileCode,
  Code,
  Shield,
  Clock,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronRight,
  ArrowUpRight,
  ArrowDownRight,
  Loader2
} from 'lucide-react';
import type {
  RepositoryTrendsResponse,
  TrendPoint,
  RepositoryListItem
} from '../types';

interface RepositoryTrendsProps {
  repositoryId: string;
  repositoryName?: string;
  githubUrl?: string;
  onLoadHistoricalRun?: (runId: string) => Promise<void>;
  loadingRunId?: string | null;
  allUserRepos?: RepositoryListItem[];
  onSelectRepo?: (repoId: string) => void;
}

function formatShortDate(dateString: string | null | undefined): string {
  if (!dateString) return '–';
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return dateString;
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
}

function formatFullDateTime(dateString: string | null | undefined): string {
  if (!dateString) return '–';
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return dateString;
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatCompactNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return '–';
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}k`;
  return num.toLocaleString();
}

/**
 * Renders a metric change badge (delta and percentage)
 * Handles inverted semantic coloring for findings (where an increase is a regression).
 */
function DeltaBadge({
  delta,
  pctChange,
  isFindings = false,
  suffix = '',
}: {
  delta: number | null;
  pctChange: number | null;
  isFindings?: boolean;
  suffix?: string;
}) {
  if (delta === null) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-zinc-850 text-zinc-400 border border-zinc-750">
        Baseline
      </span>
    );
  }

  if (delta === 0) {
    return (
      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-zinc-850 text-zinc-400 border border-zinc-750">
        <Minus className="w-3 h-3 text-zinc-500" />
        <span>0{suffix} (0.0%)</span>
      </span>
    );
  }

  const isPositive = delta > 0;
  const deltaStr = isPositive ? `+${delta.toLocaleString()}${suffix}` : `${delta.toLocaleString()}${suffix}`;
  const pctStr = pctChange !== null ? ` (${isPositive ? '+' : ''}${pctChange.toFixed(1)}%)` : '';

  if (isFindings) {
    // For findings: INCREASE is regression (rose), DECREASE is improvement (emerald)
    if (isPositive) {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-rose-950/60 text-rose-300 border border-rose-800/80">
          <ArrowUpRight className="w-3 h-3 text-rose-400" />
          <span>{deltaStr}{pctStr}</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-800/80">
        <ArrowDownRight className="w-3 h-3 text-emerald-400" />
        <span>{deltaStr}{pctStr}</span>
      </span>
    );
  }

  // Regular metrics (Lines, Files): neutral/indigo indicators
  return (
    <span
      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border ${
        isPositive
          ? 'bg-indigo-950/60 text-indigo-300 border-indigo-800/70'
          : 'bg-zinc-850 text-zinc-300 border-zinc-750'
      }`}
    >
      {isPositive ? (
        <TrendingUp className="w-3 h-3 text-indigo-400" />
      ) : (
        <TrendingDown className="w-3 h-3 text-zinc-400" />
      )}
      <span>{deltaStr}{pctStr}</span>
    </span>
  );
}

/**
 * Lightweight, production-quality responsive SVG Line Chart.
 * Zero external dependencies, pure React + SVG.
 * Handles 1 point, zero values, missing values, and responsive scaling.
 */
interface ChartSeries {
  name: string;
  data: (number | null)[];
  strokeColor: string;
  fillGradientId?: string;
  strokeDasharray?: string;
  isDashed?: boolean;
}

function SvgTrendChart({
  title,
  description,
  labels,
  series,
  points,
  yFormatter = (v: number) => v.toLocaleString(),
  isFindings = false,
}: {
  title: string;
  description?: string;
  labels: string[];
  series: ChartSeries[];
  points: TrendPoint[];
  yFormatter?: (v: number) => string;
  isFindings?: boolean;
}) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const width = 640;
  const height = 220;
  const padLeft = 55;
  const padRight = 30;
  const padTop = 25;
  const padBottom = 35;

  const chartWidth = width - padLeft - padRight;
  const chartHeight = height - padTop - padBottom;

  // Flatten all series numbers to compute bounds
  const allValues = series.flatMap(s => s.data.filter((v): v is number => v !== null && !isNaN(v)));
  const hasValues = allValues.length > 0;
  const rawMin = hasValues ? Math.min(...allValues) : 0;
  const rawMax = hasValues ? Math.max(...allValues) : 10;

  // Ensure reasonable scaling interval
  let minY = rawMin > 0 && rawMax - rawMin > rawMin * 0.5 ? Math.floor(rawMin * 0.9) : Math.min(0, rawMin);
  let maxY = rawMax === rawMin ? rawMax + 10 : Math.ceil(rawMax * 1.08);
  if (maxY === minY) maxY = minY + 10;

  const yRange = maxY - minY || 1;

  const getYCoord = (val: number | null) => {
    if (val === null || isNaN(val)) return null;
    return padTop + chartHeight - ((val - minY) / yRange) * chartHeight;
  };

  const getXCoord = (idx: number) => {
    if (labels.length <= 1) {
      return padLeft + chartWidth / 2;
    }
    return padLeft + (idx / (labels.length - 1)) * chartWidth;
  };

  // Generate 4 Y-axis grid tick levels
  const yTicks = [
    minY,
    minY + yRange * 0.33,
    minY + yRange * 0.66,
    maxY,
  ];

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-5 space-y-3 relative">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-zinc-850 pb-3">
        <div>
          <h4 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
            {title}
          </h4>
          {description && <p className="text-xs text-zinc-400 mt-0.5">{description}</p>}
        </div>

        {/* Legend */}
        {series.length > 1 && (
          <div className="flex items-center space-x-4 text-xs">
            {series.map(s => (
              <div key={s.name} className="flex items-center space-x-1.5">
                <span
                  className="w-3 h-0.5 rounded-full"
                  style={{ backgroundColor: s.strokeColor }}
                />
                <span className="text-zinc-400 text-[11px] font-medium">{s.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SVG Container */}
      <div className="w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible select-none"
        >
          <defs>
            <linearGradient id="indigoGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="cyanGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="amberGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Horizontal Grid lines and Y labels */}
          {yTicks.map((tick, i) => {
            const y = getYCoord(tick);
            if (y === null) return null;
            return (
              <g key={i}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke="#27272a"
                  strokeDasharray="4 4"
                  strokeWidth="1"
                />
                <text
                  x={padLeft - 8}
                  y={y + 4}
                  textAnchor="end"
                  fontSize="10"
                  fill="#71717a"
                  className="font-mono"
                >
                  {yFormatter(Math.round(tick))}
                </text>
              </g>
            );
          })}

          {/* X Axis Labels */}
          {labels.map((lbl, idx) => {
            const x = getXCoord(idx);
            return (
              <g key={idx}>
                <line
                  x1={x}
                  y1={padTop + chartHeight}
                  x2={x}
                  y2={padTop + chartHeight + 4}
                  stroke="#3f3f46"
                />
                <text
                  x={x}
                  y={padTop + chartHeight + 18}
                  textAnchor="middle"
                  fontSize="10"
                  fill={hoveredIndex === idx ? '#e4e4e7' : '#71717a'}
                  fontWeight={hoveredIndex === idx ? 'bold' : 'normal'}
                  className="font-mono transition-colors"
                >
                  {lbl}
                </text>
              </g>
            );
          })}

          {/* Render Area fills and lines for each series */}
          {series.map(s => {
            const validCoords: { x: number; y: number; val: number; idx: number }[] = [];
            s.data.forEach((val, idx) => {
              const y = getYCoord(val);
              if (y !== null && val !== null) {
                validCoords.push({ x: getXCoord(idx), y, val, idx });
              }
            });

            if (validCoords.length === 0) return null;

            // Line path
            let pathD = '';
            validCoords.forEach((pt, i) => {
              pathD += `${i === 0 ? 'M' : ' L'} ${pt.x} ${pt.y}`;
            });

            // Gradient Area fill (only if fillGradientId provided and >1 point)
            let areaD = '';
            if (s.fillGradientId && validCoords.length > 1) {
              const first = validCoords[0];
              const last = validCoords[validCoords.length - 1];
              const bottomY = padTop + chartHeight;
              areaD = `${pathD} L ${last.x} ${bottomY} L ${first.x} ${bottomY} Z`;
            }

            return (
              <g key={s.name}>
                {areaD && (
                  <path
                    d={areaD}
                    fill={`url(#${s.fillGradientId})`}
                    className="transition-all duration-300"
                  />
                )}
                {validCoords.length > 1 && (
                  <path
                    d={pathD}
                    fill="none"
                    stroke={s.strokeColor}
                    strokeWidth={s.isDashed ? '2' : '2.5'}
                    strokeDasharray={s.strokeDasharray}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="transition-all duration-300"
                  />
                )}

                {/* Single point fallback horizontal reference line */}
                {validCoords.length === 1 && (
                  <line
                    x1={padLeft}
                    y1={validCoords[0].y}
                    x2={width - padRight}
                    y2={validCoords[0].y}
                    stroke={s.strokeColor}
                    strokeDasharray="4 4"
                    strokeWidth="1.5"
                    strokeOpacity="0.6"
                  />
                )}

                {/* Data point dots */}
                {validCoords.map(pt => {
                  const isHovered = hoveredIndex === pt.idx;
                  return (
                    <g key={pt.idx}>
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r={isHovered ? 6 : 4}
                        fill="#09090b"
                        stroke={s.strokeColor}
                        strokeWidth={isHovered ? 3 : 2}
                        className="cursor-pointer transition-all duration-150"
                        onMouseEnter={() => setHoveredIndex(pt.idx)}
                        onMouseLeave={() => setHoveredIndex(null)}
                      />
                    </g>
                  );
                })}
              </g>
            );
          })}

          {/* Hover guideline */}
          {hoveredIndex !== null && (
            <line
              x1={getXCoord(hoveredIndex)}
              y1={padTop}
              x2={getXCoord(hoveredIndex)}
              y2={padTop + chartHeight}
              stroke="#6366f1"
              strokeDasharray="2 2"
              strokeWidth="1"
              strokeOpacity="0.8"
            />
          )}
        </svg>
      </div>

      {/* Interactive Tooltip Card when hovering a point */}
      {hoveredIndex !== null && points[hoveredIndex] && (
        <div className="mt-2 p-3 bg-zinc-950 border border-zinc-700/80 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs shadow-lg animate-fade-in">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-indigo-300 font-semibold">
              #{points[hoveredIndex].analysis_id.slice(0, 8)}
            </span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                points[hoveredIndex].analysis_type === 'ai'
                  ? 'bg-violet-950 text-violet-300 border border-violet-800'
                  : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
              }`}
            >
              {points[hoveredIndex].analysis_type === 'ai' ? 'AI Review' : 'Deterministic'}
            </span>
            <span className="text-zinc-400 text-[11px]">
              {formatFullDateTime(points[hoveredIndex].created_at)}
            </span>
          </div>

          <div className="flex items-center space-x-4">
            {series.map(s => {
              const val = s.data[hoveredIndex];
              return (
                <div key={s.name} className="flex items-center space-x-1.5">
                  <span className="text-zinc-400 font-medium">{s.name}:</span>
                  <span className="font-bold text-white">
                    {val !== null ? val.toLocaleString() : '–'}
                  </span>
                </div>
              );
            })}

            {/* If hovering findings chart, show regression/improvement note */}
            {isFindings && (
              <DeltaBadge
                delta={points[hoveredIndex].delta_findings_count}
                pctChange={points[hoveredIndex].pct_change_findings_count}
                isFindings={true}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function RepositoryTrends({
  repositoryId,
  repositoryName = 'Repository',
  githubUrl,
  onLoadHistoricalRun,
  loadingRunId,
  allUserRepos = [],
  onSelectRepo,
}: RepositoryTrendsProps) {
  const [trendsData, setTrendsData] = useState<RepositoryTrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrends = useCallback(async (repoId: string) => {
    if (!repoId) return;
    setLoading(true);
    setError(null);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/repositories/${repoId}/trends`, {
        credentials: 'include',
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to load trends (${res.status})`);
      }
      const data: RepositoryTrendsResponse = await res.json();
      setTrendsData(data);
    } catch (err: any) {
      console.error('Error fetching repository trends:', err);
      setError(err.message || 'Could not load historical analysis trends.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTrends(repositoryId);
  }, [repositoryId, fetchTrends]);

  const trends = trendsData?.trends || [];
  const latestPoint: TrendPoint | null = trends.length > 0 ? trends[trends.length - 1] : null;

  // Chart labels: short date for each point
  const chartLabels = trends.map((p) => {
    const shortDate = formatShortDate(p.created_at);
    return `${shortDate} (#${p.analysis_id.slice(0, 4)})`;
  });

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Header & Repository Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-indigo-950/80 border border-indigo-800/70 text-indigo-400 shadow-sm">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-xl font-bold text-white tracking-tight">
                  Analysis Trends & Metric Trajectory
                </h3>
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800/70">
                  {trends.length} {trends.length === 1 ? 'run' : 'runs'}
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                Chronological comparisons across completed static scans and AI engineering reviews.
              </p>
            </div>
          </div>
        </div>

        {/* Repository Switcher / GitHub link */}
        <div className="flex items-center space-x-3">
          {allUserRepos.length > 1 && onSelectRepo && (
            <div className="flex items-center space-x-1.5 text-xs">
              <span className="text-zinc-500 font-medium">Switch:</span>
              <select
                value={repositoryId}
                onChange={e => onSelectRepo(e.target.value)}
                className="bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500/80 transition-colors"
              >
                {allUserRepos.map(r => (
                  <option key={r.id} value={r.id}>
                    {r.owner}/{r.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => fetchTrends(repositoryId)}
            disabled={loading}
            title="Refresh trends data"
            className="p-2 rounded-xl text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850 border border-zinc-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>

          {githubUrl && (
            <a
              href={githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1 text-xs text-zinc-400 hover:text-zinc-200 px-3 py-1.5 rounded-xl bg-zinc-900 border border-zinc-800 hover:border-zinc-700 transition-colors"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && !trendsData && (
        <div className="space-y-6 animate-pulse">
          {/* Top KPI Skeletons */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-4 space-y-2">
                <div className="h-3 bg-zinc-800 rounded w-1/2" />
                <div className="h-6 bg-zinc-750 rounded w-3/4" />
                <div className="h-3 bg-zinc-850 rounded w-2/3" />
              </div>
            ))}
          </div>

          {/* Chart Skeletons */}
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-6 h-64 flex items-center justify-center">
            <div className="flex items-center space-x-2 text-xs text-zinc-400">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Fetching chronological trend data from PostgreSQL...</span>
            </div>
          </div>
        </div>
      )}

      {/* Error State with Retry Button */}
      {error && (
        <div className="bg-rose-950/30 border border-rose-800/80 p-6 rounded-2xl flex items-start space-x-3.5 text-xs text-rose-200 shadow-xl">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-2 flex-1">
            <h4 className="font-bold text-sm text-rose-100">Failed to load repository trends</h4>
            <p className="text-rose-300/90 leading-relaxed">{error}</p>
            <button
              onClick={() => fetchTrends(repositoryId)}
              className="mt-2 inline-flex items-center space-x-1.5 px-3.5 py-1.5 bg-rose-900/80 hover:bg-rose-800 text-rose-100 rounded-xl text-xs font-semibold transition-colors shadow-sm cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      )}

      {/* Empty State: 0 runs */}
      {!loading && !error && trends.length === 0 && (
        <div className="text-center py-16 px-4 space-y-4 bg-zinc-900/20 border border-zinc-850 rounded-2xl">
          <div className="w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto text-zinc-500">
            <Activity className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h4 className="text-base font-bold text-zinc-200">No completed analysis runs yet</h4>
            <p className="text-xs text-zinc-400 max-w-md mx-auto leading-relaxed">
              When you run Deep Static Scans or Gemini AI Reviews, completed runs will automatically populate here to track code lines, files, and findings over time.
            </p>
          </div>
        </div>
      )}

      {/* Empty State: 1 run (Requirement 12: fewer than 2 runs exist) */}
      {!loading && !error && trends.length === 1 && latestPoint && (
        <div className="space-y-6">
          {/* Top Single Run KPI */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-4 space-y-1">
              <span className="text-xxs font-bold uppercase tracking-wider text-zinc-500">Runs Analyzed</span>
              <p className="text-2xl font-black text-white">1</p>
              <span className="text-[11px] text-zinc-400">Baseline run recorded</span>
            </div>

            <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-4 space-y-1">
              <span className="text-xxs font-bold uppercase tracking-wider text-zinc-500">Total Lines</span>
              <p className="text-2xl font-black text-white">
                {latestPoint.total_lines?.toLocaleString() || '–'}
              </p>
              <span className="text-[11px] text-zinc-400">
                {latestPoint.code_lines?.toLocaleString() || '0'} code lines
              </span>
            </div>

            <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-4 space-y-1">
              <span className="text-xxs font-bold uppercase tracking-wider text-zinc-500">Total Files</span>
              <p className="text-2xl font-black text-white">
                {latestPoint.total_files?.toLocaleString() || '–'}
              </p>
              <span className="text-[11px] text-zinc-400">Tracked in codebase</span>
            </div>

            <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-4 space-y-1">
              <span className="text-xxs font-bold uppercase tracking-wider text-zinc-500">Findings Count</span>
              <p className="text-2xl font-black text-amber-400">
                {latestPoint.findings_count?.toLocaleString() || '0'}
              </p>
              <span className="text-[11px] text-zinc-400">Initial baseline findings</span>
            </div>
          </div>

          {/* Educational notice card */}
          <div className="p-6 rounded-2xl bg-zinc-900/30 border border-indigo-900/50 text-center space-y-3">
            <div className="w-12 h-12 rounded-xl bg-indigo-950/80 border border-indigo-800/80 text-indigo-400 flex items-center justify-center mx-auto">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="space-y-1 max-w-lg mx-auto">
              <h4 className="text-sm font-bold text-zinc-200">
                Historical Trends Require at Least 2 Completed Runs
              </h4>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Currently, 1 analysis run has been completed for <strong>{repositoryName}</strong>. Once you run an additional Deep Scan or AI Review, DevLens will calculate historical deltas, growth rates, and regression trajectories.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Trends View: 2 or more runs */}
      {!loading && !error && trends.length >= 2 && latestPoint && (
        <div className="space-y-8">
          
          {/* Top Compact Summary KPIs (Requirement 10) */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
            
            {/* 1. Runs Analyzed */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 space-y-1.5">
              <span className="text-xxs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-400" /> Runs Analyzed
              </span>
              <p className="text-2xl font-black text-white tracking-tight">
                {trendsData?.total_runs_analyzed || trends.length}
              </p>
              <div className="text-[11px] text-zinc-400 flex items-center space-x-1">
                <span>Deterministic & AI</span>
              </div>
            </div>

            {/* 2. Latest Run Date */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 space-y-1.5">
              <span className="text-xxs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-zinc-400" /> Latest Run Date
              </span>
              <p className="text-sm font-bold text-zinc-100 truncate mt-1">
                {formatShortDate(latestPoint.created_at)}
              </p>
              <div className="text-[11px] text-zinc-500 truncate">
                {formatFullDateTime(latestPoint.created_at).split(',')[1]?.trim() || ''}
              </div>
            </div>

            {/* 3. Latest Findings */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 space-y-1.5">
              <span className="text-xxs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-amber-400" /> Latest Findings
              </span>
              <div className="flex items-baseline space-x-2">
                <p className="text-2xl font-black text-amber-400">
                  {latestPoint.findings_count !== null ? latestPoint.findings_count.toLocaleString() : '0'}
                </p>
              </div>
              <div>
                <DeltaBadge
                  delta={latestPoint.delta_findings_count}
                  pctChange={latestPoint.pct_change_findings_count}
                  isFindings={true}
                />
              </div>
            </div>

            {/* 4. Latest Lines */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 space-y-1.5">
              <span className="text-xxs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                <Code className="w-3.5 h-3.5 text-indigo-400" /> Latest Lines
              </span>
              <p className="text-2xl font-black text-white tracking-tight">
                {latestPoint.code_lines !== null ? formatCompactNumber(latestPoint.code_lines) : '–'}
              </p>
              <div>
                <DeltaBadge
                  delta={latestPoint.delta_code_lines}
                  pctChange={latestPoint.pct_change_code_lines}
                />
              </div>
            </div>

            {/* 5. Latest Files */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 space-y-1.5">
              <span className="text-xxs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-cyan-400" /> Latest Files
              </span>
              <p className="text-2xl font-black text-white tracking-tight">
                {latestPoint.total_files !== null ? latestPoint.total_files.toLocaleString() : '–'}
              </p>
              <div>
                <DeltaBadge
                  delta={latestPoint.delta_total_files}
                  pctChange={latestPoint.pct_change_total_files}
                />
              </div>
            </div>

          </div>

          {/* Visualized Charts Section (Requirements 5, 6, 7) */}
          <div className="space-y-6">
            
            {/* Chart 1: Code Volume (Lines of Code & Total Lines) */}
            <SvgTrendChart
              title="Code Volume & Line Trends"
              description="Track growth and refactoring patterns in code lines and total repository lines."
              labels={chartLabels}
              points={trends}
              series={[
                {
                  name: 'Code Lines',
                  data: trends.map(p => p.code_lines),
                  strokeColor: '#6366f1',
                  fillGradientId: 'indigoGradient',
                },
                {
                  name: 'Total Lines',
                  data: trends.map(p => p.total_lines),
                  strokeColor: '#a855f7',
                  isDashed: true,
                  strokeDasharray: '4 4',
                },
              ]}
              yFormatter={v => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toString())}
            />

            {/* Dual Grid: Files & Findings */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Chart 2: Total Files */}
              <SvgTrendChart
                title="Codebase File Count"
                description="Chronological volume of tracked source files."
                labels={chartLabels}
                points={trends}
                series={[
                  {
                    name: 'Total Files',
                    data: trends.map(p => p.total_files),
                    strokeColor: '#06b6d4',
                    fillGradientId: 'cyanGradient',
                  },
                ]}
                yFormatter={v => v.toString()}
              />

              {/* Chart 3: Findings Count (Security & Quality) */}
              <SvgTrendChart
                title="Security & Quality Findings Trajectory"
                description="Decrease indicates resolved issues; increase flags code regressions."
                labels={chartLabels}
                points={trends}
                isFindings={true}
                series={[
                  {
                    name: 'Findings',
                    data: trends.map(p => p.findings_count),
                    strokeColor: '#f59e0b',
                    fillGradientId: 'amberGradient',
                  },
                ]}
                yFormatter={v => v.toString()}
              />

            </div>
          </div>

          {/* Detailed Chronological History Table */}
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-850 pb-3">
              <div>
                <h4 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-indigo-400" /> Chronological Run Audit
                </h4>
                <p className="text-xs text-zinc-400">Every recorded analysis execution and calculated deltas.</p>
              </div>
              <span className="text-xxs font-mono text-zinc-500">
                Sorted by created_at asc
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-400 font-semibold text-xxs uppercase tracking-wider">
                    <th className="py-2.5 px-3">Run ID</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Code Lines</th>
                    <th className="py-2.5 px-3">Total Lines</th>
                    <th className="py-2.5 px-3">Total Files</th>
                    <th className="py-2.5 px-3">Findings</th>
                    {onLoadHistoricalRun && <th className="py-2.5 px-3 text-right">Action</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-850 font-mono text-[11px]">
                  {trends.map((point, index) => {
                    const isAi = point.analysis_type === 'ai';
                    const isFirst = index === 0;
                    const isLoading = loadingRunId === point.analysis_id;

                    return (
                      <tr key={point.analysis_id} className="hover:bg-zinc-850/40 transition-colors">
                        <td className="py-3 px-3 font-bold text-zinc-300">
                          #{point.analysis_id.slice(0, 8)}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              isAi
                                ? 'bg-violet-950 text-violet-300 border border-violet-800'
                                : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                            }`}
                          >
                            {isAi ? 'AI Review' : 'Deterministic'}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-zinc-400 font-sans">
                          {formatFullDateTime(point.created_at)}
                        </td>
                        <td className="py-3 px-3 text-zinc-200">
                          <span>{point.code_lines?.toLocaleString() || '–'}</span>
                          {!isFirst && point.delta_code_lines !== null && (
                            <span className="ml-2 text-xxs text-zinc-400">
                              ({point.delta_code_lines > 0 ? '+' : ''}{point.delta_code_lines})
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-zinc-200">
                          <span>{point.total_lines?.toLocaleString() || '–'}</span>
                          {!isFirst && point.delta_total_lines !== null && (
                            <span className="ml-2 text-xxs text-zinc-400">
                              ({point.delta_total_lines > 0 ? '+' : ''}{point.delta_total_lines})
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-zinc-200">
                          <span>{point.total_files?.toLocaleString() || '–'}</span>
                          {!isFirst && point.delta_total_files !== null && (
                            <span className="ml-2 text-xxs text-zinc-400">
                              ({point.delta_total_files > 0 ? '+' : ''}{point.delta_total_files})
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-amber-400">
                              {point.findings_count !== null ? point.findings_count.toLocaleString() : '0'}
                            </span>
                            <DeltaBadge
                              delta={point.delta_findings_count}
                              pctChange={point.pct_change_findings_count}
                              isFindings={true}
                            />
                          </div>
                        </td>
                        {onLoadHistoricalRun && (
                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={() => onLoadHistoricalRun(point.analysis_id)}
                              disabled={isLoading}
                              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-indigo-950/80 hover:bg-indigo-900 border border-indigo-800/80 text-indigo-200 text-xxs font-sans font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                            >
                              {isLoading ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                <>
                                  <span>View Report</span>
                                  <ChevronRight className="w-3 h-3" />
                                </>
                              )}
                            </button>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
