import React, { useState, useEffect } from 'react';
import {
  History,
  X,
  RefreshCw,
  Trash2,
  Database,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  CheckCircle2,
  AlertCircle,
  Clock,
  Code,
  FileCode,
  AlertTriangle,
  Loader2,
  Star,
  Search,
  Check
} from 'lucide-react';
import type { RepositoryListItem, AnalysisRunSummary } from '../types';

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  repositories: RepositoryListItem[];
  reposLoading: boolean;
  reposError: string | null;
  onRefreshRepos: () => void;
  onLoadRun: (runId: string) => Promise<void>;
  loadingRunId: string | null;
  onDeleteRepo: (repoId: string) => Promise<void>;
  deletingRepoId: string | null;
  currentActiveRunId?: string | null;
}

function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatDateTime(dateString: string | null | undefined): string {
  if (!dateString) return '–';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export default function HistoryDrawer({
  isOpen,
  onClose,
  repositories,
  reposLoading,
  reposError,
  onRefreshRepos,
  onLoadRun,
  loadingRunId,
  onDeleteRepo,
  deletingRepoId,
  currentActiveRunId,
}: HistoryDrawerProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [runsError, setRunsError] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Fetch analysis runs when a repository is selected/expanded
  useEffect(() => {
    if (!selectedRepoId) return;

    let isMounted = true;
    const fetchHistory = async () => {
      setRunsLoading(true);
      setRunsError(null);
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/repositories/${selectedRepoId}/analyses?limit=25`, {
          credentials: 'include',
        });
        if (!res.ok) {
          throw new Error(`Failed to load runs: ${res.status}`);
        }
        const data: AnalysisRunSummary[] = await res.json();
        if (isMounted) setRuns(data);
      } catch (err: any) {
        console.error('Error fetching repo history:', err);
        if (isMounted) setRunsError(err.message || 'Could not load analysis history.');
      } finally {
        if (isMounted) setRunsLoading(false);
      }
    };

    fetchHistory();
    return () => {
      isMounted = false;
    };
  }, [selectedRepoId]);

  if (!isOpen) return null;

  const filteredRepos = repositories.filter(r => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    return (
      r.name.toLowerCase().includes(query) ||
      r.owner.toLowerCase().includes(query) ||
      (r.language && r.language.toLowerCase().includes(query))
    );
  });

  const handleToggleRepo = (repoId: string) => {
    if (selectedRepoId === repoId) {
      setSelectedRepoId(null);
      setRuns([]);
      setRunsError(null);
    } else {
      setSelectedRepoId(repoId);
    }
  };

  const handleConfirmDelete = async (e: React.MouseEvent, repoId: string) => {
    e.stopPropagation();
    if (confirmDeleteId === repoId) {
      await onDeleteRepo(repoId);
      setConfirmDeleteId(null);
      if (selectedRepoId === repoId) {
        setSelectedRepoId(null);
      }
    } else {
      setConfirmDeleteId(repoId);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-xl bg-zinc-900 border-l border-zinc-800 shadow-2xl flex flex-col">
          
          {/* Drawer Header */}
          <div className="px-6 py-5 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-md flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-indigo-950/80 border border-indigo-800/80 text-indigo-400">
                <History className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h2 className="text-base font-bold text-zinc-100">Repository History</h2>
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-950/90 text-indigo-300 border border-indigo-800/70">
                    {repositories.length} {repositories.length === 1 ? 'repo' : 'repos'}
                  </span>
                </div>
                <p className="text-xs text-zinc-400">View and load previously analyzed repositories from PostgreSQL</p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={onRefreshRepos}
                disabled={reposLoading}
                title="Refresh repository list"
                className="p-2 rounded-xl text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 border border-transparent hover:border-zinc-700 transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${reposLoading ? 'animate-spin text-indigo-400' : ''}`} />
              </button>
              <button
                onClick={onClose}
                className="p-2 rounded-xl text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 border border-transparent hover:border-zinc-700 transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Search Bar */}
          {repositories.length > 0 && (
            <div className="p-4 border-b border-zinc-800/80 bg-zinc-900/50">
              <div className="relative">
                <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter repositories by name or language..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-9 pr-4 py-2 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500/80 transition-colors"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="text-zinc-500 hover:text-zinc-300 absolute right-3 top-1/2 -translate-y-1/2 text-xs"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Drawer Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            
            {/* Loading Skeleton */}
            {reposLoading && repositories.length === 0 && (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="bg-zinc-950/60 border border-zinc-800/80 rounded-2xl p-4 animate-pulse space-y-3">
                    <div className="h-4 bg-zinc-800 rounded w-1/2" />
                    <div className="h-3 bg-zinc-800/60 rounded w-3/4" />
                    <div className="h-3 bg-zinc-850 rounded w-1/3" />
                  </div>
                ))}
              </div>
            )}

            {/* Error State */}
            {reposError && (
              <div className="bg-rose-950/40 border border-rose-800/80 p-4 rounded-2xl flex items-start space-x-3 text-xs text-rose-200">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="space-y-1 flex-1">
                  <p className="font-semibold">Failed to load repositories</p>
                  <p className="text-rose-300/80">{reposError}</p>
                  <button
                    onClick={onRefreshRepos}
                    className="mt-2 inline-flex items-center space-x-1.5 px-3 py-1 bg-rose-900/60 hover:bg-rose-900 text-rose-100 rounded-lg text-xs font-semibold transition-colors"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Retry</span>
                  </button>
                </div>
              </div>
            )}

            {/* Empty State */}
            {!reposLoading && !reposError && repositories.length === 0 && (
              <div className="text-center py-12 px-4 space-y-3 bg-zinc-950/40 border border-zinc-850 rounded-2xl">
                <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto text-zinc-500">
                  <Database className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-bold text-zinc-200">No repositories analyzed yet</h3>
                <p className="text-xs text-zinc-400 max-w-sm mx-auto">
                  When you run a Quick Ingestion, Deep Static Scan, or Gemini AI Review, your analyzed repositories will be stored here for instant retrieval.
                </p>
              </div>
            )}

            {/* Repositories List */}
            {filteredRepos.map(repo => {
              const isSelected = selectedRepoId === repo.id;
              const isDeleting = deletingRepoId === repo.id;
              const latest = repo.latest_analysis;

              return (
                <div
                  key={repo.id}
                  className={`bg-zinc-950/70 border rounded-2xl transition-all duration-200 overflow-hidden ${
                    isSelected ? 'border-indigo-500/60 shadow-lg shadow-indigo-950/20' : 'border-zinc-800/80 hover:border-zinc-700'
                  }`}
                >
                  {/* Repo Card Header */}
                  <div
                    onClick={() => handleToggleRepo(repo.id)}
                    className="p-4.5 cursor-pointer hover:bg-zinc-900/40 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1.5 flex-1 min-w-0">
                        
                        {/* Owner & Name */}
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-bold text-zinc-100 truncate hover:text-indigo-300 transition-colors">
                            {repo.owner} / <span className="text-white">{repo.name}</span>
                          </span>
                          {repo.stars > 0 && (
                            <span className="inline-flex items-center space-x-1 text-[11px] text-zinc-400">
                              <Star className="w-3 h-3 text-amber-400 fill-amber-400/20" />
                              <span>{repo.stars}</span>
                            </span>
                          )}
                        </div>

                        {/* Badges & Meta */}
                        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                          {/* Language */}
                          {repo.language && (
                            <span className="px-2 py-0.5 rounded-full font-medium bg-zinc-850 text-zinc-300 border border-zinc-750">
                              {repo.language}
                            </span>
                          )}

                          {/* Latest Status */}
                          {latest && (
                            <span
                              className={`px-2 py-0.5 rounded-full font-semibold inline-flex items-center space-x-1 border ${
                                latest.status === 'completed'
                                  ? 'bg-emerald-950/50 text-emerald-300 border-emerald-800/70'
                                  : latest.status === 'failed'
                                  ? 'bg-rose-950/50 text-rose-300 border-rose-800/70'
                                  : 'bg-amber-950/50 text-amber-300 border-amber-800/70'
                              }`}
                            >
                              {latest.status === 'completed' && <CheckCircle2 className="w-2.5 h-2.5" />}
                              {latest.status === 'failed' && <AlertCircle className="w-2.5 h-2.5" />}
                              <span className="capitalize">{latest.status}</span>
                            </span>
                          )}

                          {/* Latest Type */}
                          {latest && (
                            <span
                              className={`px-2 py-0.5 rounded-full font-semibold border ${
                                latest.analysis_type === 'ai'
                                  ? 'bg-violet-950/60 text-violet-300 border-violet-800/70'
                                  : 'bg-cyan-950/60 text-cyan-300 border-cyan-800/70'
                              }`}
                            >
                              {latest.analysis_type === 'ai' ? 'AI Review' : 'Deterministic'}
                            </span>
                          )}

                          {/* Relative Time */}
                          <span className="text-zinc-500 inline-flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>{formatRelativeTime(repo.last_analyzed_at || repo.updated_at)}</span>
                          </span>
                        </div>

                        {/* Metric Summary Pill */}
                        {latest && (latest.total_lines !== null || latest.total_files !== null) && (
                          <div className="flex items-center space-x-3 text-[11px] text-zinc-400 pt-1">
                            {latest.total_lines !== null && (
                              <span className="inline-flex items-center space-x-1">
                                <Code className="w-3 h-3 text-zinc-500" />
                                <span>{latest.total_lines.toLocaleString()} lines</span>
                              </span>
                            )}
                            {latest.total_files !== null && (
                              <span className="inline-flex items-center space-x-1">
                                <FileCode className="w-3 h-3 text-zinc-500" />
                                <span>{latest.total_files} files</span>
                              </span>
                            )}
                            {latest.findings_count !== null && (
                              <span className="inline-flex items-center space-x-1 text-amber-400/90">
                                <AlertTriangle className="w-3 h-3 text-amber-400" />
                                <span>{latest.findings_count} findings</span>
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Actions Right */}
                      <div className="flex items-center space-x-1 shrink-0 pt-0.5">
                        {/* Delete Action */}
                        <button
                          onClick={e => handleConfirmDelete(e, repo.id)}
                          disabled={isDeleting}
                          title={confirmDeleteId === repo.id ? 'Click again to confirm deletion' : 'Delete repository'}
                          className={`p-1.5 rounded-lg text-xs transition-colors ${
                            confirmDeleteId === repo.id
                              ? 'bg-red-950 text-red-300 border border-red-700'
                              : 'text-zinc-500 hover:text-rose-400 hover:bg-zinc-800'
                          }`}
                        >
                          {isDeleting ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : confirmDeleteId === repo.id ? (
                            <span className="text-[10px] font-bold px-1 text-red-300">Confirm?</span>
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" />
                          )}
                        </button>

                        {/* Expand Chevron */}
                        <div className="text-zinc-500 pl-1">
                          {isSelected ? (
                            <ChevronDown className="w-4 h-4 text-indigo-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Analysis History Section */}
                  {isSelected && (
                    <div className="border-t border-zinc-850/80 bg-zinc-900/30 p-4 space-y-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-zinc-300">Past Analysis Runs</span>
                        <a
                          href={repo.github_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-zinc-500 hover:text-zinc-300 inline-flex items-center space-x-1 text-[11px]"
                        >
                          <span>Open on GitHub</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>

                      {/* Runs Loading */}
                      {runsLoading && (
                        <div className="flex items-center justify-center py-6 space-x-2 text-xs text-zinc-400">
                          <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                          <span>Loading historical runs...</span>
                        </div>
                      )}

                      {/* Runs Error */}
                      {runsError && (
                        <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-900 text-xs text-rose-300 space-y-1">
                          <p>{runsError}</p>
                          <button
                            onClick={() => handleToggleRepo(repo.id)}
                            className="font-semibold underline hover:text-white"
                          >
                            Retry
                          </button>
                        </div>
                      )}

                      {/* Runs List */}
                      {!runsLoading && !runsError && runs.length === 0 && (
                        <p className="text-xs text-zinc-500 py-3 text-center">
                          No analysis runs found for this repository.
                        </p>
                      )}

                      {!runsLoading && !runsError && runs.length > 0 && (
                        <div className="space-y-2">
                          {runs.map(run => {
                            const isLoadingThis = loadingRunId === run.id;
                            const isActive = currentActiveRunId === run.id;

                            return (
                              <div
                                key={run.id}
                                className={`p-3 rounded-xl border transition-all ${
                                  isActive
                                    ? 'bg-indigo-950/30 border-indigo-700/80 shadow-sm'
                                    : 'bg-zinc-950/90 border-zinc-800 hover:border-zinc-700'
                                }`}
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <div className="space-y-1">
                                    <div className="flex items-center space-x-2">
                                      <span className="font-mono text-[11px] text-zinc-300 font-semibold">
                                        #{run.id.slice(0, 8)}
                                      </span>
                                      
                                      {/* Type */}
                                      <span
                                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                          run.analysis_type === 'ai'
                                            ? 'bg-violet-950 text-violet-300 border border-violet-800'
                                            : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                                        }`}
                                      >
                                        {run.analysis_type === 'ai' ? 'AI Review' : 'Deterministic'}
                                      </span>

                                      {/* Status */}
                                      <span
                                        className={`px-1.5 py-0.2 rounded text-[10px] font-semibold ${
                                          run.status === 'completed'
                                            ? 'text-emerald-400'
                                            : run.status === 'failed'
                                            ? 'text-rose-400'
                                            : 'text-amber-400'
                                        }`}
                                      >
                                        {run.status}
                                      </span>
                                    </div>

                                    <div className="text-[11px] text-zinc-500 flex items-center space-x-2">
                                      <span>Created: {formatDateTime(run.created_at)}</span>
                                      {run.completed_at && (
                                        <span>• Completed: {formatDateTime(run.completed_at)}</span>
                                      )}
                                    </div>
                                  </div>

                                  {/* Action button */}
                                  <div>
                                    {isActive ? (
                                      <span className="inline-flex items-center space-x-1 text-[11px] font-bold text-indigo-400 bg-indigo-950/80 border border-indigo-800/80 px-2.5 py-1 rounded-lg">
                                        <Check className="w-3 h-3" />
                                        <span>Active</span>
                                      </span>
                                    ) : run.status === 'completed' ? (
                                      <button
                                        onClick={() => onLoadRun(run.id)}
                                        disabled={isLoadingThis}
                                        className="inline-flex items-center space-x-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-3 py-1 rounded-lg text-xs transition-colors shadow-sm active:scale-95 disabled:opacity-50"
                                      >
                                        {isLoadingThis ? (
                                          <>
                                            <Loader2 className="w-3 h-3 animate-spin" />
                                            <span>Loading...</span>
                                          </>
                                        ) : (
                                          <>
                                            <Database className="w-3 h-3" />
                                            <span>Load Report</span>
                                          </>
                                        )}
                                      </button>
                                    ) : (
                                      <span className="text-[11px] text-zinc-500 capitalize">{run.status}</span>
                                    )}
                                  </div>
                                </div>

                                {run.error_message && (
                                  <p className="mt-2 text-[11px] text-rose-400/90 bg-rose-950/30 p-2 rounded border border-rose-900/60">
                                    {run.error_message}
                                  </p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Drawer Footer */}
          <div className="p-4 border-t border-zinc-800/80 bg-zinc-950/70 text-xs text-zinc-500 flex items-center justify-between">
            <span className="inline-flex items-center space-x-1.5">
              <Database className="w-3.5 h-3.5 text-zinc-400" />
              <span>DevLens Persistence Layer • PostgreSQL 16</span>
            </span>
            <button
              onClick={onClose}
              className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
