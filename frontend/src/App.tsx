import React, { useState, useEffect } from 'react';
import { 
  Terminal, 
  Shield, 
  Search, 
  Code, 
  CheckCircle2, 
  ExternalLink,
  FileCode,
  Gauge,
  Folder,
  File,
  GitFork,
  Star,
  AlertCircle,
  AlertTriangle,
  Info,
  FileText,
  BarChart3
} from 'lucide-react';
import type { AnalyzeResponse, AnalysisReport, Finding } from './types';

const GithubIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    viewBox="0 0 24 24"
    width="24"
    height="24"
    stroke="currentColor"
    strokeWidth="2"
    fill="none"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
    <path d="M9 18c-4.51 2-5-2-7-2" />
  </svg>
);

interface HealthStatus {
  status: string;
  project: string;
  features: {
    database_integrated: boolean;
    ai_analysis_integrated: boolean;
  };
}

type TabType = 'overview' | 'metrics' | 'languages' | 'findings' | 'files';

export default function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [backendInfo, setBackendInfo] = useState<HealthStatus | null>(null);
  
  // Phase 3 Ingestion & Scan Types state
  const [scanType, setScanType] = useState<'quick' | 'deep'>('deep');
  const [quickData, setQuickData] = useState<AnalyzeResponse | null>(null);
  const [reportData, setReportData] = useState<AnalysisReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  
  // Findings state filters
  const [severityFilter, setSeverityFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'>('all');

  // Ping backend health endpoint on mount to verify CORS connectivity
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/health`);
        if (response.ok) {
          const data: HealthStatus = await response.json();
          setBackendStatus('connected');
          setBackendInfo(data);
        } else {
          setBackendStatus('disconnected');
        }
      } catch (error) {
        console.error('Failed to connect to backend API:', error);
        setBackendStatus('disconnected');
      }
    };
    checkBackendHealth();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setIsSubmitting(true);
    setErrorMsg(null);
    setQuickData(null);
    setReportData(null);
    setActiveTab('overview');

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const endpoint = scanType === 'deep' 
      ? `${apiUrl}/api/repositories/analyze/report` 
      : `${apiUrl}/api/repositories/analyze`;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: repoUrl }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = errorData.detail || `Request failed with status ${response.status}`;
        throw new Error(detail);
      }

      const payload = await response.json();
      if (scanType === 'deep') {
        setReportData(payload as AnalysisReport);
      } else {
        setQuickData(payload as AnalyzeResponse);
      }
    } catch (err: any) {
      console.error('Ingestion failed:', err);
      setErrorMsg(err.message || 'An unexpected error occurred while communicating with the DevLens API.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getActiveRepository = () => {
    if (reportData) return reportData.repository;
    if (quickData) return quickData.repository;
    return null;
  };

  const getActiveTree = () => {
    if (reportData) return reportData.tree;
    if (quickData) return quickData.tree;
    return [];
  };

  // Helper to sort tree items: directories first, then files, both alphabetically
  const getSortedTree = () => {
    const tree = getActiveTree();
    return [...tree].sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === 'directory' ? -1 : 1;
      }
      return a.path.localeCompare(b.path);
    });
  };

  // Filter findings based on selected severity filter
  const getFilteredFindings = (): Finding[] => {
    if (!reportData) return [];
    if (severityFilter === 'all') return reportData.findings;
    return reportData.findings.filter(f => f.severity === severityFilter);
  };

  // Helper colors for findings severity badges
  const getSeverityBadgeClass = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-950/40 text-red-400 border-red-800/80';
      case 'high':
        return 'bg-orange-950/40 text-orange-400 border-orange-800/80';
      case 'medium':
        return 'bg-amber-950/40 text-amber-400 border-amber-800/80';
      case 'low':
        return 'bg-blue-950/40 text-blue-400 border-blue-800/80';
      default:
        return 'bg-zinc-800 text-zinc-400 border-zinc-700';
    }
  };

  const repository = getActiveRepository();

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-indigo-500 selection:text-white flex flex-col justify-between">
      
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-indigo-900/30">
              <Terminal className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
                DevLens
              </span>
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
                v0.3.0-alpha
              </span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="hidden md:flex space-x-1">
            <a href="#dashboard" className="px-4 py-2 rounded-lg text-sm font-medium bg-zinc-800 text-white border border-zinc-700">
              Dashboard
            </a>
            <a href="#docs" className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition duration-200">
              Docs
            </a>
            <a href="https://github.com" target="_blank" rel="noreferrer" className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition duration-200 flex items-center gap-1.5">
              GitHub <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </nav>

          {/* Connection Status */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <span className="relative flex h-2 w-2">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  backendStatus === 'connected' ? 'bg-emerald-400' : backendStatus === 'disconnected' ? 'bg-red-400' : 'bg-amber-400'
                }`}></span>
                <span className={`relative inline-flex rounded-full h-2 w-2 ${
                  backendStatus === 'connected' ? 'bg-emerald-500' : backendStatus === 'disconnected' ? 'bg-red-500' : 'bg-amber-500'
                }`}></span>
              </span>
              <span className="text-xs text-zinc-400 font-medium">
                {backendStatus === 'checking' && 'API Checking...'}
                {backendStatus === 'connected' && `API Online (${backendInfo?.project || 'DevLens'})`}
                {backendStatus === 'disconnected' && 'API Offline'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl w-full mx-auto px-6 py-8 flex-grow space-y-10">
        
        {/* Banner Section */}
        <section className="text-center space-y-4 max-w-3xl mx-auto py-2">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-b from-white via-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Deterministic Analysis Engine
          </h1>
          <p className="text-zinc-400 text-base leading-relaxed">
            Ingest repositories to inspect structure, calculate precise code metrics, and scan for potential quality concerns or hardcoded secrets.
          </p>
        </section>

        {/* Action Panel: Repository Input */}
        <section className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 md:p-8 shadow-xl backdrop-blur-sm max-w-4xl mx-auto">
          <div className="space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Search className="w-5 h-5 text-indigo-500" />
                  Analyze Codebase
                </h2>
                <p className="text-zinc-400 text-xs mt-0.5">
                  Analyze public repositories. (Phase 3 runs local metrics and credential checks).
                </p>
              </div>
              
              {/* Scan Type selector */}
              <div className="bg-zinc-950 p-1 rounded-xl border border-zinc-800 flex items-center space-x-1 text-xs self-start sm:self-center">
                <button
                  type="button"
                  onClick={() => setScanType('quick')}
                  className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
                    scanType === 'quick' 
                      ? 'bg-zinc-800 text-white border border-zinc-700' 
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  Quick Ingestion (Phase 2)
                </button>
                <button
                  type="button"
                  onClick={() => setScanType('deep')}
                  className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
                    scanType === 'deep' 
                      ? 'bg-zinc-800 text-white border border-zinc-700' 
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  Deep Analysis Report (Phase 3)
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-grow">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500">
                  <GithubIcon className="w-5 h-5" />
                </div>
                <input
                  type="url"
                  required
                  placeholder="https://github.com/owner/repository"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 bg-zinc-950/80 border border-zinc-800 focus:border-indigo-500 rounded-xl text-zinc-100 placeholder-zinc-600 focus:outline-none transition duration-200 text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-6 py-3 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:from-zinc-800 disabled:to-zinc-800 disabled:text-zinc-500 text-white font-semibold rounded-xl text-sm transition duration-200 flex items-center justify-center gap-2 shadow-lg shadow-indigo-900/20 active:scale-98 cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    {scanType === 'deep' ? 'Analyzing Code...' : 'Ingesting Repository...'}
                  </>
                ) : (
                  <>
                    {scanType === 'deep' ? 'Run Code Analysis' : 'Ingest Tree'}
                  </>
                )}
              </button>
            </form>
          </div>
        </section>

        {/* Dashboard Content states */}
        
        {/* Loading Spinner */}
        {isSubmitting && (
          <section className="space-y-6 max-w-5xl mx-auto animate-pulse">
            <div className="h-6 w-52 bg-zinc-800 rounded"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-28 bg-zinc-900/50 border border-zinc-800 rounded-xl"></div>
              ))}
            </div>
            <div className="h-64 bg-zinc-900/50 border border-zinc-800 rounded-xl"></div>
          </section>
        )}

        {/* Error State */}
        {errorMsg && !isSubmitting && (
          <section className="max-w-2xl mx-auto bg-red-950/20 border border-red-800/80 rounded-2xl p-6 flex items-start space-x-4 animate-fade-in shadow-lg">
            <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="space-y-2">
              <h3 className="text-lg font-bold text-red-400">Analysis Execution Error</h3>
              <p className="text-zinc-400 text-sm leading-relaxed">{errorMsg}</p>
              <button 
                onClick={() => setErrorMsg(null)}
                className="mt-2 text-xs font-semibold text-zinc-300 hover:text-white px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg transition"
              >
                Dismiss Error
              </button>
            </div>
          </section>
        )}

        {/* Success States */}
        {repository && !isSubmitting && !errorMsg && (
          <section className="space-y-8 max-w-7xl mx-auto animate-fade-in">
            {/* Header info */}
            <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-zinc-800 pb-4 gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-2xl font-bold tracking-tight text-white">{repository.name}</h3>
                  <a 
                    href={repository.url} 
                    target="_blank" 
                    rel="noreferrer" 
                    className="text-zinc-500 hover:text-indigo-400 transition"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
                <p className="text-sm text-zinc-500">
                  Owner: <span className="font-semibold text-zinc-400">{repository.owner}</span> | Branch: <span className="font-mono text-indigo-400">{repository.default_branch}</span>
                </p>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-xs text-indigo-400 font-semibold px-3 py-1.5 rounded-full bg-indigo-950/30 border border-indigo-800/50 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> {reportData ? 'Deep Analysis Complete' : 'Quick Scan Complete'}
                </span>
              </div>
            </div>

            {/* Quick Scan Visuals (Phase 2) */}
            {quickData && !reportData && (
              <div className="space-y-8">
                {/* Stats */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'Stars', value: repository.stars, icon: Star, color: 'text-amber-500' },
                    { label: 'Forks', value: repository.forks, icon: GitFork, color: 'text-zinc-400' },
                    { label: 'Open Issues', value: repository.open_issues, icon: AlertCircle, color: 'text-red-500' },
                    { label: 'Language', value: repository.language || 'Unknown', icon: Code, color: 'text-indigo-400' },
                  ].map((card, i) => (
                    <div key={i} className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-5">
                      <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">{card.label}</p>
                      <div className="flex items-baseline space-x-2 mt-2">
                        <p className="text-3xl font-extrabold text-zinc-100">{card.value.toLocaleString()}</p>
                        {card.icon && <card.icon className={`w-4 h-4 ${card.color}`} />}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Tree and Details */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Metadata */}
                  <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 space-y-4">
                    <h4 className="font-bold text-zinc-200 text-sm border-b border-zinc-800 pb-2">Description</h4>
                    <p className="text-xs text-zinc-300 leading-relaxed">
                      {repository.description || 'No description provided.'}
                    </p>
                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 text-xxs font-mono text-zinc-500">
                      <p>Scanner: DevLens Ingestion v0.2</p>
                      <p>Tree: {quickData.tree.length} files scanned</p>
                    </div>
                  </div>

                  {/* Tree */}
                  <div className="lg:col-span-2 bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 flex flex-col h-[400px]">
                    <h4 className="font-bold text-zinc-200 text-sm border-b border-zinc-800 pb-2 flex items-center gap-2">
                      <Folder className="w-4 h-4 text-indigo-400" /> File Tree
                    </h4>
                    <div className="flex-grow overflow-y-auto mt-4 font-mono text-xs pr-2 space-y-1.5 custom-scrollbar">
                      {getSortedTree().map((item, idx) => {
                        const segments = item.path.split('/');
                        const name = segments[segments.length - 1];
                        return (
                          <div key={idx} style={{ paddingLeft: `${(segments.length - 1) * 18}px` }} className="flex items-center space-x-2 py-0.5 hover:bg-zinc-800/40 rounded transition">
                            {item.type === 'directory' ? <Folder className="w-4 h-4 text-amber-500/80" /> : <File className="w-4 h-4 text-zinc-400" />}
                            <span>{name}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Deep Analysis Visuals (Phase 3) */}
            {reportData && (
              <div className="space-y-6">
                
                {/* Skip Notification Alerts */}
                {reportData.summary.skipped_files > 0 && (
                  <div className="bg-amber-950/20 border border-amber-900/80 rounded-2xl p-5 flex items-start space-x-3.5">
                    <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5 animate-pulse" />
                    <div className="space-y-1 text-xs">
                      <h5 className="font-bold text-amber-400">Analysis Limits Info</h5>
                      <p className="text-zinc-400 leading-relaxed">
                        Some codebase files were skipped due to scanner limits: Capped files count (max 100), file size threshold (max 200KB), or binary formats.
                      </p>
                      <div className="flex items-center gap-4 mt-2 font-semibold text-zinc-500">
                        <span>Too Large: {reportData.analysis_metadata.skip_reasons.too_large}</span>
                        <span>•</span>
                        <span>Unsupported/Binary: {reportData.analysis_metadata.skip_reasons.unsupported}</span>
                        <span>•</span>
                        <span>Limit Exceeded: {reportData.analysis_metadata.skip_reasons.limit_exceeded}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab selectors */}
                <div className="flex border-b border-zinc-800 overflow-x-auto text-sm">
                  {[
                    { id: 'overview', label: 'Overview', icon: Gauge },
                    { id: 'metrics', label: 'Metrics', icon: FileText },
                    { id: 'languages', label: 'Languages', icon: BarChart3 },
                    { id: 'findings', label: 'Findings', icon: Shield, count: reportData.findings.length },
                    { id: 'files', label: 'File Tree', icon: Folder }
                  ].map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as TabType)}
                      className={`px-5 py-3 border-b-2 font-medium flex items-center gap-2 transition whitespace-nowrap cursor-pointer ${
                        activeTab === tab.id 
                          ? 'border-indigo-500 text-white' 
                          : 'border-transparent text-zinc-500 hover:text-zinc-300'
                      }`}
                    >
                      <tab.icon className="w-4 h-4" />
                      {tab.label}
                      {tab.count !== undefined && (
                        <span className={`text-xxs font-bold px-1.5 py-0.5 rounded-full ${
                          tab.count > 0 ? 'bg-indigo-950 text-indigo-400 border border-indigo-800' : 'bg-zinc-800 text-zinc-600'
                        }`}>
                          {tab.count}
                        </span>
                      )}
                    </button>
                  ))}
                </div>

                {/* Tab Panels */}
                
                {/* 1. Overview Tab */}
                {activeTab === 'overview' && (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
                    {/* General summary counts */}
                    <div className="lg:col-span-2 bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 space-y-6">
                      <h4 className="font-bold text-zinc-200 text-sm border-b border-zinc-800 pb-2">Repository File Categories</h4>
                      
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                        {[
                          { label: 'Total Files', count: reportData.summary.total_files, icon: FilesIcon },
                          { label: 'Analyzed Files', count: reportData.summary.analyzed_files, icon: CheckCircle2, color: 'text-indigo-400' },
                          { label: 'Skipped Files', count: reportData.summary.skipped_files, icon: AlertTriangle, color: reportData.summary.skipped_files > 0 ? 'text-amber-500' : 'text-zinc-500' },
                          { label: 'Source Files', count: reportData.summary.source_files, icon: FileCode },
                          { label: 'Test Files', count: reportData.summary.test_files, icon: TestIcon },
                          { label: 'Config Files', count: reportData.summary.configuration_files, icon: ConfigIcon },
                          { label: 'Documentation', count: reportData.summary.documentation_files, icon: FileText },
                          { label: 'Asset Files', count: reportData.summary.asset_files, icon: ImageIcon },
                          { label: 'Unknown Files', count: reportData.summary.unknown_files, icon: File }
                        ].map((stat, i) => (
                          <div key={i} className="bg-zinc-950 p-4 rounded-xl border border-zinc-800/80">
                            <span className="text-xxs text-zinc-500 uppercase tracking-wider font-semibold block">{stat.label}</span>
                            <p className="text-2xl font-bold text-white mt-1">{stat.count}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Quick description & metrics panel */}
                    <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 space-y-6">
                      <h4 className="font-bold text-zinc-200 text-sm border-b border-zinc-800 pb-2">Description</h4>
                      <p className="text-xs text-zinc-300 leading-relaxed">
                        {repository.description || 'No description provided.'}
                      </p>
                      
                      <div className="space-y-4 pt-4 border-t border-zinc-800 text-xs">
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Stars:</span>
                          <span className="font-bold text-zinc-300">{repository.stars.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Forks:</span>
                          <span className="font-bold text-zinc-300">{repository.forks.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Open Issues:</span>
                          <span className="font-bold text-zinc-300">{repository.open_issues.toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. Code Metrics Tab */}
                {activeTab === 'metrics' && (
                  <div className="space-y-6 animate-fade-in">
                    {/* Line count stats */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      {[
                        { label: 'Total Lines', count: reportData.metrics.total_lines, desc: 'Sum of all parsed files' },
                        { label: 'Code Lines', count: reportData.metrics.code_lines, desc: 'Excluding comments & blanks', color: 'text-indigo-400' },
                        { label: 'Comment Lines', count: reportData.metrics.comment_lines, desc: 'Block and inline comments', color: 'text-emerald-400' },
                        { label: 'Blank Lines', count: reportData.metrics.blank_lines, desc: 'Empty whitespace lines', color: 'text-zinc-500' }
                      ].map((item, idx) => (
                        <div key={idx} className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-5">
                          <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">{item.label}</span>
                          <p className={`text-3xl font-extrabold mt-2 ${item.color || 'text-white'}`}>
                            {item.count.toLocaleString()}
                          </p>
                          <p className="text-xxs text-zinc-600 mt-2">{item.desc}</p>
                        </div>
                      ))}
                    </div>

                    {/* Progress distribution bar */}
                    {reportData.metrics.total_lines > 0 && (
                      <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 space-y-4">
                        <h4 className="font-bold text-zinc-200 text-xs">Lines Composition</h4>
                        <div className="h-4 w-full bg-zinc-950 rounded-lg overflow-hidden flex text-xxs font-bold text-center">
                          <div 
                            style={{ width: `${(reportData.metrics.code_lines / reportData.metrics.total_lines) * 100}%` }} 
                            className="bg-indigo-600 text-white flex items-center justify-center"
                          >
                            {Math.round((reportData.metrics.code_lines / reportData.metrics.total_lines) * 100)}% Code
                          </div>
                          <div 
                            style={{ width: `${(reportData.metrics.comment_lines / reportData.metrics.total_lines) * 100}%` }} 
                            className="bg-emerald-600 text-white flex items-center justify-center"
                          >
                            {Math.round((reportData.metrics.comment_lines / reportData.metrics.total_lines) * 100)}% Comments
                          </div>
                          <div 
                            style={{ width: `${(reportData.metrics.blank_lines / reportData.metrics.total_lines) * 100}%` }} 
                            className="bg-zinc-700 text-zinc-300 flex items-center justify-center"
                          >
                            {Math.round((reportData.metrics.blank_lines / reportData.metrics.total_lines) * 100)}% Blanks
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Largest files panel */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* By size */}
                      <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6">
                        <h4 className="font-bold text-zinc-200 text-xs border-b border-zinc-800 pb-2 mb-4">Largest Files by Size</h4>
                        <div className="space-y-3 font-mono text-xs">
                          {reportData.metrics.largest_files_by_size.map((file, idx) => (
                            <div key={idx} className="flex justify-between items-center py-1 hover:bg-zinc-800/20 px-2 rounded">
                              <span className="text-zinc-300 truncate max-w-[70%]" title={file.path}>{file.path}</span>
                              <span className="text-zinc-500 font-semibold">{(file.size_bytes / 1024).toFixed(2)} KB</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* By lines */}
                      <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6">
                        <h4 className="font-bold text-zinc-200 text-xs border-b border-zinc-800 pb-2 mb-4">Largest Files by Line Count</h4>
                        <div className="space-y-3 font-mono text-xs">
                          {reportData.metrics.largest_files_by_lines.map((file, idx) => (
                            <div key={idx} className="flex justify-between items-center py-1 hover:bg-zinc-800/20 px-2 rounded">
                              <span className="text-zinc-300 truncate max-w-[70%]" title={file.path}>{file.path}</span>
                              <span className="text-indigo-400 font-semibold">{file.line_count.toLocaleString()} lines</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                  </div>
                )}

                {/* 3. Languages Tab */}
                {activeTab === 'languages' && (
                  <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 space-y-6 animate-fade-in max-w-4xl mx-auto">
                    <h4 className="font-bold text-zinc-200 text-sm border-b border-zinc-800 pb-2 mb-4">Language Composition</h4>
                    
                    <div className="space-y-5">
                      {reportData.languages.map((lang, idx) => (
                        <div key={idx} className="space-y-2">
                          <div className="flex justify-between text-xs font-semibold">
                            <span className="text-zinc-300">{lang.language}</span>
                            <span className="text-zinc-400">
                              {lang.file_count} {lang.file_count === 1 ? 'file' : 'files'} ({lang.percentage}%)
                            </span>
                          </div>
                          
                          {/* Percentage progress bar */}
                          <div className="w-full bg-zinc-950 h-2 rounded-full overflow-hidden">
                            <div 
                              style={{ width: `${lang.percentage}%` }} 
                              className="bg-indigo-600 h-full rounded-full"
                            ></div>
                          </div>
                        </div>
                      ))}
                      
                      {reportData.languages.length === 0 && (
                        <p className="text-center text-zinc-500 text-xs py-8">No supported source code files detected.</p>
                      )}
                    </div>
                  </div>
                )}

                {/* 4. Findings Tab */}
                {activeTab === 'findings' && (
                  <div className="space-y-6 animate-fade-in">
                    
                    {/* Severity Filters */}
                    <div className="flex flex-wrap items-center gap-2 border-b border-zinc-800 pb-4">
                      <span className="text-xs text-zinc-500 font-bold uppercase mr-2">Severity:</span>
                      {[
                        { id: 'all', label: 'All Findings' },
                        { id: 'critical', label: 'Critical' },
                        { id: 'high', label: 'High' },
                        { id: 'medium', label: 'Medium' },
                        { id: 'low', label: 'Low' },
                        { id: 'info', label: 'Info' }
                      ].map(filter => (
                        <button
                          key={filter.id}
                          onClick={() => setSeverityFilter(filter.id as any)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition cursor-pointer ${
                            severityFilter === filter.id 
                              ? 'bg-indigo-600 text-white border-indigo-500' 
                              : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'
                          }`}
                        >
                          {filter.label}
                        </button>
                      ))}
                    </div>

                    {/* Findings list */}
                    <div className="space-y-4 max-w-5xl mx-auto">
                      {getFilteredFindings().map((finding, idx) => (
                        <div key={idx} className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-5 hover:border-zinc-700/80 transition space-y-3">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-zinc-800 pb-2">
                            <div className="flex flex-wrap items-center gap-2.5">
                              <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${getSeverityBadgeClass(finding.severity)}`}>
                                {finding.severity}
                              </span>
                              <h5 className="font-bold text-sm text-zinc-200">{finding.title}</h5>
                            </div>
                            <span className="text-[10px] bg-zinc-800 text-zinc-400 border border-zinc-700 font-semibold px-2 py-0.5 rounded-md uppercase">
                              {finding.category}
                            </span>
                          </div>

                          <div className="space-y-2 text-xs">
                            <p className="text-zinc-300 leading-relaxed">{finding.description}</p>
                            
                            <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 font-mono text-xxs text-zinc-500">
                              File: <span className="text-zinc-300">{finding.file}</span> (Line: {finding.line})
                            </div>
                            
                            <div className="text-zinc-400 pt-1 flex items-start space-x-1.5">
                              <Info className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                              <p><span className="font-semibold text-zinc-300">Recommendation:</span> {finding.recommendation}</p>
                            </div>
                          </div>
                        </div>
                      ))}

                      {getFilteredFindings().length === 0 && (
                        <div className="text-center py-12 border border-zinc-800 bg-zinc-900/10 rounded-2xl space-y-3">
                          <CheckCircle2 className="w-8 h-8 text-zinc-700 mx-auto" />
                          <h5 className="font-bold text-zinc-300 text-sm">No findings reported</h5>
                          <p className="text-xs text-zinc-500 max-w-xs mx-auto">
                            No static issues matching this filter were detected by the rule scanners.
                          </p>
                        </div>
                      )}
                    </div>

                  </div>
                )}

                {/* 5. File Tree Tab */}
                {activeTab === 'files' && (
                  <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 flex flex-col h-[480px] animate-fade-in max-w-5xl mx-auto">
                    <div className="border-b border-zinc-800 pb-3 flex justify-between items-center">
                      <h4 className="font-bold text-zinc-200 text-sm flex items-center gap-2">
                        <Folder className="w-4 h-4 text-indigo-400" /> File Tree
                      </h4>
                      <span className="text-xs text-zinc-500">{reportData.tree.length} entries</span>
                    </div>

                    <div className="flex-grow overflow-y-auto mt-4 font-mono text-xs pr-2 space-y-1.5 custom-scrollbar select-none">
                      {getSortedTree().map((item, idx) => {
                        const pathSegments = item.path.split('/');
                        const name = pathSegments[pathSegments.length - 1];
                        const depth = pathSegments.length - 1;
                        
                        return (
                          <div 
                            key={idx} 
                            style={{ paddingLeft: `${depth * 18}px` }} 
                            className="flex items-center space-x-2 py-0.5 hover:bg-zinc-800/40 rounded transition"
                          >
                            {item.type === 'directory' ? (
                              <Folder className="w-4 h-4 text-amber-500/80 flex-shrink-0" />
                            ) : (
                              <File className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                            )}
                            <span className={item.type === 'directory' ? 'text-zinc-200 font-semibold' : 'text-zinc-300'}>
                              {name}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

              </div>
            )}

          </section>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 bg-zinc-950/80 py-8 px-6 text-center text-xs text-zinc-600">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-indigo-500/60" />
            <span className="font-bold text-zinc-400">DevLens Project</span>
            <span>|</span>
            <span>Phase 3 Scanners</span>
          </div>
          <div>
            Tech Stack: React, Vite, TS, Tailwind CSS v4, FastAPI, Docker
          </div>
          <div>
            &copy; {new Date().getFullYear()} DevLens. All rights reserved.
          </div>
        </div>
      </footer>

    </div>
  );
}

// Dummy Icon placeholders for custom category icons
const FilesIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-4 h-4 text-zinc-500" {...props}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
  </svg>
);
const TestIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-4 h-4 text-indigo-400" {...props}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
  </svg>
);
const ConfigIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-4 h-4 text-zinc-400" {...props}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.43l-1.003.828c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.552 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.43l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.645-.869l.214-1.28Z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
  </svg>
);
const ImageIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-4 h-4 text-zinc-500" {...props}>
    <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375 0 1 1-.75 0 .375 0 0 1 .75 0Z" />
  </svg>
);
