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
  BarChart3,
  Sparkles,
  Zap,
  Check,
  Layers,
  Activity,
  ArrowRight,
  LogOut,
  User as UserIcon
} from 'lucide-react';
import type { 
  AnalyzeResponse, 
  AnalysisReport, 
  Finding, 
  AIAnalysisReport, 
  AIAnalyzeResponse,
  AssessmentRating,
  PriorityLevel,
  User
} from './types';

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


type TabType = 'overview' | 'metrics' | 'languages' | 'findings' | 'files' | 'ai-review';

const AI_LOADING_STAGES = [
  "Ingesting repository & calculating metrics",
  "Reviewing architecture & module design",
  "Evaluating application security posture",
  "Assessing code maintainability & quality",
  "Synthesizing actionable engineering priorities"
];

export default function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  
  // Ingestion, Scan Types & AI state
  const [scanType, setScanType] = useState<'quick' | 'deep' | 'ai'>('ai');
  const [quickData, setQuickData] = useState<AnalyzeResponse | null>(null);
  const [reportData, setReportData] = useState<AnalysisReport | null>(null);
  const [aiData, setAiData] = useState<AIAnalysisReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [aiStage, setAiStage] = useState(0);
  
  // Findings state filters
  const [severityFilter, setSeverityFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'>('all');

  // Authentication state (Phase 5B)
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // Check current authenticated user and handle OAuth error redirects
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/auth/me`, {
          credentials: 'include',
        });
        if (res.ok) {
          const userData: User = await res.json();
          setCurrentUser(userData);
        } else {
          setCurrentUser(null);
        }
      } catch (err) {
        setCurrentUser(null);
      } finally {
        setAuthLoading(false);
      }
    };

    const params = new URLSearchParams(window.location.search);
    const authErr = params.get('auth_error');
    if (authErr) {
      setAuthError(authErr === 'access_denied' ? 'GitHub authorization was cancelled or denied.' : `GitHub sign-in error: ${authErr}`);
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    checkAuth();
  }, []);

  const handleLogin = () => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    window.location.href = `${apiUrl}/api/auth/github/login`;
  };

  const handleLogout = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      await fetch(`${apiUrl}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (err) {
      console.error('Logout failed:', err);
    } finally {
      setCurrentUser(null);
    }
  };

  // Ping backend health endpoint on mount to verify CORS connectivity
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/health`);
        if (response.ok) {
          setBackendStatus('connected');
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

  // Cycle through AI loading stages while request is running
  useEffect(() => {
    let interval: any;
    if (isSubmitting && scanType === 'ai') {
      setAiStage(0);
      interval = setInterval(() => {
        setAiStage(prev => (prev + 1) % AI_LOADING_STAGES.length);
      }, 2200);
    }
    return () => clearInterval(interval);
  }, [isSubmitting, scanType]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    if (!currentUser) {
      setErrorMsg("Please sign in with GitHub to analyze repositories.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    setQuickData(null);
    setReportData(null);
    setAiData(null);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    let endpoint = `${apiUrl}/api/repositories/analyze`;
    if (scanType === 'deep') {
      endpoint = `${apiUrl}/api/repositories/analyze/report`;
    } else if (scanType === 'ai') {
      endpoint = `${apiUrl}/api/repositories/analyze/ai`;
    }

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'include',
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
      if (scanType === 'ai') {
        const aiResponse = payload as AIAnalyzeResponse;
        setReportData(aiResponse.deterministic_analysis);
        setAiData(aiResponse.ai_analysis);
        setActiveTab('ai-review');
      } else if (scanType === 'deep') {
        setReportData(payload as AnalysisReport);
        setActiveTab('overview');
      } else {
        setQuickData(payload as AnalyzeResponse);
        setActiveTab('overview');
      }
    } catch (err: any) {
      console.error('Analysis failed:', err);
      setErrorMsg(err.message || 'An unexpected error occurred while communicating with the DevLens API.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRunAiReviewFromExisting = async () => {
    if (!repoUrl.trim()) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    setScanType('ai');

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${apiUrl}/api/repositories/analyze/ai`, {
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

      const payload: AIAnalyzeResponse = await response.json();
      setReportData(payload.deterministic_analysis);
      setAiData(payload.ai_analysis);
      setActiveTab('ai-review');
    } catch (err: any) {
      console.error('AI Review failed:', err);
      setErrorMsg(err.message || 'AI Review could not be completed.');
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

  // Helper colors for AI ratings
  const renderRatingBadge = (rating: AssessmentRating | string) => {
    switch (rating) {
      case 'excellent':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800">
            Excellent
          </span>
        );
      case 'good':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-950/80 text-blue-400 border border-blue-800">
            Good
          </span>
        );
      case 'fair':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-950/80 text-amber-400 border border-amber-800">
            Fair
          </span>
        );
      case 'needs_attention':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-orange-950/80 text-orange-400 border border-orange-800">
            Needs Attention
          </span>
        );
      case 'poor':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-950/80 text-red-400 border border-red-800">
            Poor
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-zinc-800 text-zinc-400 border border-zinc-700">
            {rating}
          </span>
        );
    }
  };

  // Helper colors for AI priority badges
  const renderPriorityBadge = (priority: PriorityLevel | string) => {
    switch (priority) {
      case 'critical':
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-extrabold bg-red-950/90 text-red-400 border border-red-700 tracking-wider">
            CRITICAL
          </span>
        );
      case 'high':
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-extrabold bg-orange-950/90 text-orange-400 border border-orange-700 tracking-wider">
            HIGH
          </span>
        );
      case 'medium':
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-extrabold bg-amber-950/90 text-amber-400 border border-amber-700 tracking-wider">
            MEDIUM
          </span>
        );
      case 'low':
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-extrabold bg-blue-950/90 text-blue-400 border border-blue-700 tracking-wider">
            LOW
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-extrabold bg-zinc-800 text-zinc-300 border border-zinc-700">
            {priority.toUpperCase()}
          </span>
        );
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
            <div className="bg-gradient-to-tr from-violet-600 via-indigo-600 to-purple-500 p-2.5 rounded-xl shadow-lg shadow-indigo-900/30">
              <Terminal className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
                DevLens
              </span>
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-violet-950/70 text-violet-300 border border-violet-800/80">
                Phase 4 • Gemini AI
              </span>
            </div>
          </div>

          {/* Header right: Health status + User Auth */}
          <div className="flex items-center space-x-4 text-xs">
            {backendStatus === 'checking' && (
              <div className="flex items-center space-x-2 text-zinc-400">
                <div className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                <span>Connecting...</span>
              </div>
            )}
            {backendStatus === 'connected' && (
              <div className="flex items-center space-x-2 text-emerald-400 bg-emerald-950/30 border border-emerald-900 px-3 py-1.5 rounded-full">
                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Connected</span>
              </div>
            )}
            {backendStatus === 'disconnected' && (
              <div className="flex items-center space-x-2 text-rose-400 bg-rose-950/30 border border-rose-900 px-3 py-1.5 rounded-full">
                <div className="w-2 h-2 rounded-full bg-rose-500" />
                <span>Offline</span>
              </div>
            )}

            {/* Auth status action */}
            {authLoading ? (
              <div className="w-24 h-8 bg-zinc-800/70 animate-pulse rounded-xl" />
            ) : currentUser ? (
              <div className="flex items-center space-x-2.5 bg-zinc-900/90 border border-zinc-750 pl-2 pr-3 py-1 rounded-full shadow-sm">
                {currentUser.avatar_url ? (
                  <img
                    src={currentUser.avatar_url}
                    alt={currentUser.github_login}
                    className="w-5 h-5 rounded-full border border-zinc-700"
                  />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-indigo-900/80 flex items-center justify-center text-indigo-300">
                    <UserIcon className="w-3 h-3" />
                  </div>
                )}
                <span className="font-semibold text-zinc-200">{currentUser.github_login}</span>
                <button
                  onClick={handleLogout}
                  title="Sign out"
                  className="text-zinc-400 hover:text-rose-400 transition-colors ml-1 p-0.5 rounded"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={handleLogin}
                className="inline-flex items-center space-x-2 bg-gradient-to-r from-zinc-800 to-zinc-850 hover:from-zinc-700 hover:to-zinc-750 text-zinc-100 border border-zinc-700 px-3.5 py-1.5 rounded-xl font-medium shadow-sm transition-all hover:border-zinc-500 active:scale-95"
              >
                <GithubIcon className="w-3.5 h-3.5 text-white" />
                <span>Sign in with GitHub</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-6 py-10 space-y-10">
        
        {/* Auth Error Banner */}
        {authError && (
          <div className="max-w-4xl mx-auto bg-amber-950/40 border border-amber-800/80 text-amber-200 px-4 py-3 rounded-xl flex items-center justify-between text-sm shadow-md">
            <div className="flex items-center space-x-2.5">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>{authError}</span>
            </div>
            <button
              onClick={() => setAuthError(null)}
              className="text-amber-400 hover:text-amber-200 font-bold ml-4"
            >
              ✕
            </button>
          </div>
        )}

        {/* Hero Section */}
        <section className="text-center space-y-3 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-violet-950/60 text-violet-300 border border-violet-800/80 mb-2">
            <Sparkles className="w-3.5 h-3.5 text-violet-400" />
            AI Intelligence Layer + Deterministic Code Analysis
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-b from-white via-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            AI-Powered Engineering Reviewer
          </h1>
          <p className="text-zinc-400 text-base leading-relaxed">
            Ingest GitHub repositories for precise static metrics, security vulnerability scans, and deep architectural assessments generated by Google Gemini.
          </p>
        </section>

        {/* Action Panel: Repository Input */}
        <section className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 md:p-8 shadow-xl backdrop-blur-sm max-w-4xl mx-auto">
          <div className="space-y-5">
            {!currentUser && !authLoading && (
              <div className="bg-indigo-950/40 border border-indigo-800/60 rounded-xl p-3.5 flex items-center justify-between text-xs text-indigo-200">
                <div className="flex items-center space-x-2.5">
                  <Shield className="w-4 h-4 text-indigo-400 shrink-0" />
                  <span>GitHub authentication is required to analyze repositories and manage scan ownership.</span>
                </div>
                <button
                  type="button"
                  onClick={handleLogin}
                  className="font-semibold text-indigo-300 hover:text-white underline ml-3 shrink-0"
                >
                  Sign in now →
                </button>
              </div>
            )}

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Search className="w-5 h-5 text-indigo-500" />
                  Analyze Codebase
                </h2>
                <p className="text-zinc-400 text-xs mt-0.5">
                  Select your analysis depth and enter any public repository URL.
                </p>
              </div>
              
              {/* Scan Type selector */}
              <div className="bg-zinc-950 p-1 rounded-xl border border-zinc-800 flex items-center space-x-1 text-xs self-start sm:self-center flex-wrap gap-1">
                <button
                  type="button"
                  onClick={() => setScanType('ai')}
                  className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 ${
                    scanType === 'ai' 
                      ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-md shadow-indigo-900/40' 
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5 text-violet-300" />
                  AI Review (Phase 4)
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
                  Deep Static (Phase 3)
                </button>
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
                className="px-6 py-3 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:from-zinc-800 disabled:to-zinc-800 disabled:text-zinc-500 text-white font-semibold rounded-xl text-sm transition duration-200 flex items-center justify-center gap-2 shadow-lg shadow-indigo-900/20 active:scale-98 cursor-pointer whitespace-nowrap"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Analyzing...
                  </>
                ) : (
                  <>
                    {scanType === 'ai' && <Sparkles className="w-4 h-4 text-violet-200" />}
                    {scanType === 'ai' ? 'Run AI Review' : scanType === 'deep' ? 'Run Code Analysis' : 'Ingest Tree'}
                  </>
                )}
              </button>
            </form>
          </div>
        </section>

        {/* AI Loading Experience */}
        {isSubmitting && scanType === 'ai' && (
          <section className="max-w-2xl mx-auto bg-zinc-900/40 border border-indigo-900/40 rounded-2xl p-8 text-center space-y-5 animate-fade-in shadow-xl">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-900/40 animate-pulse">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-xl font-bold text-white">Analyzing repository with DevLens AI...</h3>
              <p className="text-sm text-indigo-400 font-medium transition-all duration-300">
                {AI_LOADING_STAGES[aiStage]}...
              </p>
              <p className="text-xs text-zinc-500">
                Unified analysis synthesizing deterministic metrics and curated source evidence.
              </p>
            </div>
            <div className="flex justify-center gap-2 max-w-xs mx-auto pt-2">
              {AI_LOADING_STAGES.map((_, idx) => (
                <div
                  key={idx}
                  className={`h-1.5 rounded-full transition-all duration-300 ${
                    idx === aiStage ? 'w-8 bg-indigo-500' : idx < aiStage ? 'w-4 bg-indigo-800/60' : 'w-4 bg-zinc-800'
                  }`}
                />
              ))}
            </div>
          </section>
        )}

        {/* Error notification banner */}
        {errorMsg && (
          <div className="bg-red-950/30 border border-red-900/80 rounded-2xl p-5 text-red-300 text-sm flex items-start space-x-3.5 max-w-4xl mx-auto">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-400 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-red-200">Analysis Request Failed</p>
              <p className="text-xs text-red-300/90 leading-relaxed">{errorMsg}</p>
            </div>
          </div>
        )}

        {/* Results Container */}
        {repository && !isSubmitting && (
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
              
              <div className="flex items-center gap-3">
                {aiData && (
                  <span className="text-xs text-violet-300 font-semibold px-3 py-1.5 rounded-full bg-violet-950/50 border border-violet-800/80 flex items-center gap-1.5 shadow-sm">
                    <Sparkles className="w-3.5 h-3.5 text-violet-400" /> AI Review Ready
                  </span>
                )}
                {reportData && !aiData && (
                  <button
                    onClick={handleRunAiReviewFromExisting}
                    className="text-xs text-white font-medium px-3.5 py-1.5 rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 border border-violet-500/50 flex items-center gap-1.5 transition cursor-pointer shadow-md shadow-indigo-900/20"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-violet-200" /> Run AI Review
                  </button>
                )}
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

            {/* Deep Analysis & AI Visuals (Phase 3 & 4) */}
            {reportData && (
              <div className="space-y-6">
                
                {/* Skip Notification Alerts */}
                {reportData.summary.skipped_files > 0 && (
                  <div className="bg-amber-950/20 border border-amber-900/80 rounded-2xl p-5 flex items-start space-x-3.5">
                    <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-400 mt-0.5" />
                    <div className="space-y-1 text-xs text-amber-300">
                      <p className="font-bold text-amber-200 text-sm">Large Repository Notice</p>
                      <p className="leading-relaxed">
                        DevLens scanned {reportData.summary.analyzed_files} source files and skipped {reportData.summary.skipped_files} files exceeding size or quantity thresholds to guarantee predictable latency.
                      </p>
                    </div>
                  </div>
                )}

                {/* Navigation Tabs */}
                <div className="border-b border-zinc-800 flex space-x-2 overflow-x-auto custom-scrollbar">
                  {[
                    ...(aiData ? [{ id: 'ai-review', label: 'AI Review', icon: Sparkles, badge: 'Gemini' }] : [{ id: 'ai-review', label: 'AI Review', icon: Sparkles, badge: 'Run' }]),
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
                          ? tab.id === 'ai-review' ? 'border-violet-500 text-white font-semibold' : 'border-indigo-500 text-white' 
                          : 'border-transparent text-zinc-500 hover:text-zinc-300'
                      }`}
                    >
                      <tab.icon className={`w-4 h-4 ${tab.id === 'ai-review' ? 'text-violet-400' : ''}`} />
                      {tab.label}
                      {tab.badge && (
                        <span className="text-xxs font-bold px-1.5 py-0.5 rounded-full bg-violet-950 text-violet-300 border border-violet-800">
                          {tab.badge}
                        </span>
                      )}
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
                
                {/* 0. AI Review Tab (Phase 4) */}
                {activeTab === 'ai-review' && (
                  <div className="space-y-8 animate-fade-in">
                    {aiData ? (
                      <>
                        {/* Executive Summary & Confidence */}
                        <div className="relative overflow-hidden bg-gradient-to-br from-violet-950/30 via-zinc-900/60 to-zinc-900/30 border border-violet-900/50 rounded-2xl p-6 md:p-8 space-y-4 shadow-xl">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800/80 pb-4">
                            <div className="flex items-center gap-2.5">
                              <div className="p-2 rounded-xl bg-violet-600/20 border border-violet-500/30">
                                <Sparkles className="w-5 h-5 text-violet-400" />
                              </div>
                              <div>
                                <h4 className="font-bold text-white text-base">Executive Engineering Summary</h4>
                                <p className="text-xs text-zinc-400">Synthesized by DevLens AI based on deterministic findings and codebase architecture.</p>
                              </div>
                            </div>
                            
                            {/* Confidence badge */}
                            <div>
                              {aiData.confidence === 'high' && (
                                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950/70 text-emerald-400 border border-emerald-800/80 flex items-center gap-1.5">
                                  <CheckCircle2 className="w-3.5 h-3.5" /> High Confidence
                                </span>
                              )}
                              {aiData.confidence === 'medium' && (
                                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-950/70 text-amber-400 border border-amber-800/80 flex items-center gap-1.5">
                                  <AlertTriangle className="w-3.5 h-3.5" /> Medium Confidence
                                </span>
                              )}
                              {aiData.confidence === 'low' && (
                                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-red-950/70 text-red-400 border border-red-800/80 flex items-center gap-1.5">
                                  <AlertCircle className="w-3.5 h-3.5" /> Low Confidence
                                </span>
                              )}
                            </div>
                          </div>

                          <p className="text-zinc-200 text-sm md:text-base leading-relaxed">
                            {aiData.executive_summary}
                          </p>

                          {aiData.confidence_reason && (
                            <div className="text-xs text-amber-400/90 bg-amber-950/20 border border-amber-900/50 p-2.5 rounded-lg flex items-center gap-2">
                              <Info className="w-4 h-4 flex-shrink-0" />
                              <span>Confidence note: {aiData.confidence_reason}</span>
                            </div>
                          )}
                        </div>

                        {/* Top 2 Core Pillars: Architecture & Security */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          
                          {/* Architecture Card */}
                          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-6 space-y-4">
                            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                              <div className="flex items-center gap-2">
                                <Layers className="w-5 h-5 text-indigo-400" />
                                <h4 className="font-bold text-white text-sm">Architecture & Design</h4>
                              </div>
                              {renderRatingBadge(aiData.architecture.rating)}
                            </div>

                            <p className="text-xs text-zinc-300 leading-relaxed">
                              {aiData.architecture.assessment}
                            </p>

                            {aiData.architecture.strengths.length > 0 && (
                              <div className="space-y-1.5 pt-2">
                                <span className="text-xxs font-bold uppercase tracking-wider text-emerald-400">Strengths</span>
                                <ul className="space-y-1 text-xs text-zinc-300">
                                  {aiData.architecture.strengths.map((str, idx) => (
                                    <li key={idx} className="flex items-start gap-2">
                                      <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                                      <span>{str}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {aiData.architecture.weaknesses.length > 0 && (
                              <div className="space-y-1.5 pt-2">
                                <span className="text-xxs font-bold uppercase tracking-wider text-amber-400">Architectural Gaps</span>
                                <ul className="space-y-1 text-xs text-zinc-300">
                                  {aiData.architecture.weaknesses.map((weak, idx) => (
                                    <li key={idx} className="flex items-start gap-2">
                                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                                      <span>{weak}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>

                          {/* Security Card */}
                          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-6 space-y-4">
                            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                              <div className="flex items-center gap-2">
                                <Shield className="w-5 h-5 text-violet-400" />
                                <h4 className="font-bold text-white text-sm">Security Posture</h4>
                              </div>
                              {renderRatingBadge(aiData.security.rating)}
                            </div>

                            <p className="text-xs text-zinc-300 leading-relaxed">
                              {aiData.security.assessment}
                            </p>

                            {aiData.security.important_issues.length > 0 && (
                              <div className="space-y-1.5 pt-2">
                                <span className="text-xxs font-bold uppercase tracking-wider text-red-400">Important Concerns</span>
                                <ul className="space-y-1 text-xs text-red-300">
                                  {aiData.security.important_issues.map((iss, idx) => (
                                    <li key={idx} className="flex items-start gap-2">
                                      <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
                                      <span>{iss}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {aiData.security.recommendations.length > 0 && (
                              <div className="space-y-1.5 pt-2">
                                <span className="text-xxs font-bold uppercase tracking-wider text-indigo-400">Hardening Steps</span>
                                <ul className="space-y-1 text-xs text-zinc-300">
                                  {aiData.security.recommendations.map((rec, idx) => (
                                    <li key={idx} className="flex items-start gap-2">
                                      <ArrowRight className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                                      <span>{rec}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Secondary Pillars: Performance, Maintainability, Documentation */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          
                          {/* Performance */}
                          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5 space-y-3">
                            <div className="flex items-center justify-between border-b border-zinc-800 pb-2.5">
                              <div className="flex items-center gap-2">
                                <Zap className="w-4 h-4 text-amber-400" />
                                <h4 className="font-bold text-white text-xs">Performance</h4>
                              </div>
                              {renderRatingBadge(aiData.performance.rating)}
                            </div>
                            <p className="text-xs text-zinc-300 leading-relaxed">
                              {aiData.performance.assessment}
                            </p>
                            {aiData.performance.recommendations.length > 0 && (
                              <ul className="text-xxs text-zinc-400 space-y-1 pt-1">
                                {aiData.performance.recommendations.map((r, i) => (
                                  <li key={i} className="flex items-start gap-1.5">
                                    <span className="text-amber-400 font-bold">•</span>
                                    <span>{r}</span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>

                          {/* Maintainability */}
                          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5 space-y-3">
                            <div className="flex items-center justify-between border-b border-zinc-800 pb-2.5">
                              <div className="flex items-center gap-2">
                                <Activity className="w-4 h-4 text-emerald-400" />
                                <h4 className="font-bold text-white text-xs">Maintainability</h4>
                              </div>
                              {renderRatingBadge(aiData.maintainability.rating)}
                            </div>
                            <p className="text-xs text-zinc-300 leading-relaxed">
                              {aiData.maintainability.assessment}
                            </p>
                            {aiData.maintainability.recommendations.length > 0 && (
                              <ul className="text-xxs text-zinc-400 space-y-1 pt-1">
                                {aiData.maintainability.recommendations.map((r, i) => (
                                  <li key={i} className="flex items-start gap-1.5">
                                    <span className="text-emerald-400 font-bold">•</span>
                                    <span>{r}</span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>

                          {/* Documentation */}
                          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5 space-y-3">
                            <div className="flex items-center justify-between border-b border-zinc-800 pb-2.5">
                              <div className="flex items-center gap-2">
                                <FileText className="w-4 h-4 text-blue-400" />
                                <h4 className="font-bold text-white text-xs">Documentation</h4>
                              </div>
                              {renderRatingBadge(aiData.documentation.rating)}
                            </div>
                            <p className="text-xs text-zinc-300 leading-relaxed">
                              {aiData.documentation.assessment}
                            </p>
                            {aiData.documentation.recommendations.length > 0 && (
                              <ul className="text-xxs text-zinc-400 space-y-1 pt-1">
                                {aiData.documentation.recommendations.map((r, i) => (
                                  <li key={i} className="flex items-start gap-1.5">
                                    <span className="text-blue-400 font-bold">•</span>
                                    <span>{r}</span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        </div>

                        {/* Positive Engineering Strengths */}
                        {aiData.strengths.length > 0 && (
                          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-6 space-y-3">
                            <h4 className="font-bold text-zinc-200 text-sm flex items-center gap-2">
                              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                              Key Engineering Strengths Observed
                            </h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                              {aiData.strengths.map((str, idx) => (
                                <div key={idx} className="bg-zinc-950/70 border border-zinc-800/80 rounded-xl p-3 flex items-start gap-2.5 text-xs text-zinc-300">
                                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                                  <span>{str}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Prioritized Engineering Improvements */}
                        {aiData.priorities.length > 0 && (
                          <div className="space-y-4">
                            <div className="flex items-center justify-between">
                              <h4 className="font-bold text-white text-base flex items-center gap-2">
                                <Zap className="w-5 h-5 text-amber-400" />
                                Prioritized Engineering Recommendations
                              </h4>
                              <span className="text-xs text-zinc-500 font-mono">
                                Ordered by impact & urgency
                              </span>
                            </div>

                            <div className="space-y-4">
                              {aiData.priorities.map((item, idx) => (
                                <div 
                                  key={idx} 
                                  className={`rounded-2xl p-6 border transition-all ${
                                    item.priority === 'critical' 
                                      ? 'bg-red-950/15 border-red-900/70 shadow-lg shadow-red-950/20' 
                                      : item.priority === 'high'
                                      ? 'bg-orange-950/15 border-orange-900/70 shadow-lg shadow-orange-950/20'
                                      : item.priority === 'medium'
                                      ? 'bg-amber-950/15 border-amber-900/60'
                                      : 'bg-zinc-900/40 border-zinc-800'
                                  }`}
                                >
                                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800/80 pb-3">
                                    <div className="flex items-center gap-2.5 flex-wrap">
                                      {renderPriorityBadge(item.priority)}
                                      <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-300 border border-zinc-700">
                                        {item.category}
                                      </span>
                                      <h5 className="font-bold text-zinc-100 text-sm md:text-base">
                                        {item.title}
                                      </h5>
                                    </div>
                                  </div>

                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-xs">
                                    <div className="space-y-1">
                                      <span className="text-xxs font-bold text-zinc-500 uppercase tracking-wider">Why It Matters</span>
                                      <p className="text-zinc-300 leading-relaxed">{item.explanation}</p>
                                    </div>
                                    <div className="space-y-1">
                                      <span className="text-xxs font-bold text-indigo-400 uppercase tracking-wider">Recommended Action</span>
                                      <p className="text-zinc-200 leading-relaxed font-medium">{item.recommendation}</p>
                                    </div>
                                  </div>

                                  {item.evidence && (
                                    <div className="mt-4 pt-3 border-t border-zinc-800/60 flex items-center gap-2 text-xxs text-zinc-400 font-mono">
                                      <Code className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
                                      <span className="text-zinc-500">Evidence:</span>
                                      <span className="text-zinc-300 truncate">{item.evidence}</span>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      /* CTA if user ran deep scan first without AI */
                      <div className="bg-gradient-to-br from-violet-950/20 via-zinc-900/40 to-zinc-900/20 border border-violet-900/40 rounded-2xl p-8 text-center space-y-5 max-w-xl mx-auto my-8">
                        <div className="w-12 h-12 mx-auto rounded-2xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center">
                          <Sparkles className="w-6 h-6 text-violet-400" />
                        </div>
                        <div className="space-y-2">
                          <h4 className="text-lg font-bold text-white">Generate Gemini AI Engineering Review</h4>
                          <p className="text-xs text-zinc-400 leading-relaxed max-w-md mx-auto">
                            Transform static repository metrics and security findings into an actionable, senior-level architectural critique with prioritized engineering recommendations.
                          </p>
                        </div>
                        <button
                          onClick={handleRunAiReviewFromExisting}
                          disabled={isSubmitting}
                          className="px-6 py-2.5 rounded-xl font-semibold text-xs text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition shadow-lg shadow-indigo-900/30 cursor-pointer"
                        >
                          {isSubmitting ? 'Analyzing...' : 'Run Gemini Review Now'}
                        </button>
                      </div>
                    )}
                  </div>
                )}
                
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

                      <h4 className="font-bold text-zinc-200 text-sm border-b border-zinc-800 pb-2">LOC Metrics</h4>
                      <div className="space-y-3 text-xs">
                        <div className="flex justify-between items-center py-1 border-b border-zinc-800/40">
                          <span className="text-zinc-500">Total Lines:</span>
                          <span className="font-bold text-zinc-200 font-mono">{reportData.metrics.total_lines.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between items-center py-1 border-b border-zinc-800/40">
                          <span className="text-zinc-500">Source Code Lines:</span>
                          <span className="font-bold text-indigo-400 font-mono">{reportData.metrics.code_lines.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between items-center py-1 border-b border-zinc-800/40">
                          <span className="text-zinc-500">Comment Lines:</span>
                          <span className="font-bold text-emerald-400 font-mono">{reportData.metrics.comment_lines.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between items-center py-1">
                          <span className="text-zinc-500">Blank Lines:</span>
                          <span className="font-bold text-zinc-400 font-mono">{reportData.metrics.blank_lines.toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. Metrics Tab */}
                {activeTab === 'metrics' && (
                  <div className="space-y-6 animate-fade-in">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      
                      {/* Largest Files by Lines */}
                      <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 space-y-4">
                        <h4 className="font-bold text-zinc-200 text-sm border-b border-zinc-800 pb-2">Largest Files (By Line Count)</h4>
                        <div className="space-y-2">
                          {reportData.metrics.largest_files_by_lines.map((item, idx) => (
                            <div key={idx} className="bg-zinc-950 p-3 rounded-xl border border-zinc-800 flex justify-between items-center text-xs">
                              <span className="font-mono text-zinc-300 truncate max-w-[70%]">{item.path}</span>
                              <span className="font-bold text-indigo-400 font-mono">{item.line_count.toLocaleString()} lines</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Largest Files by Size */}
                      <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 space-y-4">
                        <h4 className="font-bold text-zinc-200 text-sm border-b border-zinc-800 pb-2">Largest Files (By Size)</h4>
                        <div className="space-y-2">
                          {reportData.metrics.largest_files_by_size.map((item, idx) => (
                            <div key={idx} className="bg-zinc-950 p-3 rounded-xl border border-zinc-800 flex justify-between items-center text-xs">
                              <span className="font-mono text-zinc-300 truncate max-w-[70%]">{item.path}</span>
                              <span className="font-bold text-emerald-400 font-mono">{(item.size_bytes / 1024).toFixed(1)} KB</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. Languages Tab */}
                {activeTab === 'languages' && (
                  <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6 space-y-6 animate-fade-in">
                    <h4 className="font-bold text-zinc-200 text-sm border-b border-zinc-800 pb-2">Language Distribution</h4>
                    
                    <div className="space-y-4">
                      {reportData.languages.map((lang, idx) => (
                        <div key={idx} className="space-y-1.5">
                          <div className="flex justify-between text-xs">
                            <span className="font-semibold text-zinc-200">{lang.language}</span>
                            <span className="text-zinc-500 font-mono">{lang.file_count} files ({lang.percentage}%)</span>
                          </div>
                          <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-gradient-to-r from-violet-500 to-indigo-500 rounded-full transition-all duration-500" 
                              style={{ width: `${lang.percentage}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 4. Findings Tab */}
                {activeTab === 'findings' && (
                  <div className="space-y-6 animate-fade-in">
                    
                    {/* Severity Filters */}
                    <div className="flex items-center space-x-2 text-xs overflow-x-auto pb-2 custom-scrollbar">
                      {(['all', 'critical', 'high', 'medium', 'low', 'info'] as const).map(sev => (
                        <button
                          key={sev}
                          onClick={() => setSeverityFilter(sev)}
                          className={`px-3 py-1.5 rounded-xl capitalize font-medium transition cursor-pointer border ${
                            severityFilter === sev 
                              ? 'bg-zinc-800 text-white border-zinc-700' 
                              : 'bg-zinc-950 text-zinc-500 border-zinc-800/80 hover:text-zinc-300'
                          }`}
                        >
                          {sev} {sev !== 'all' && `(${reportData.findings.filter(f => f.severity === sev).length})`}
                        </button>
                      ))}
                    </div>

                    {/* Findings list */}
                    {getFilteredFindings().length === 0 ? (
                      <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-12 text-center text-zinc-500 text-xs">
                        No findings detected matching current filter criteria.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {getFilteredFindings().map(finding => (
                          <div key={finding.id} className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5 space-y-2.5">
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-0.5 rounded-full text-xxs font-bold uppercase border ${getSeverityBadgeClass(finding.severity)}`}>
                                  {finding.severity}
                                </span>
                                <span className="font-bold text-zinc-200 text-sm">{finding.title}</span>
                              </div>
                              <span className="text-xxs font-mono text-zinc-500">{finding.category}</span>
                            </div>

                            <p className="text-xs text-zinc-400">{finding.description}</p>

                            <div className="flex items-center gap-4 text-xxs font-mono text-zinc-500 pt-1">
                              <span>File: <span className="text-zinc-300">{finding.file}</span></span>
                              <span>Line: <span className="text-indigo-400">{finding.line}</span></span>
                            </div>

                            {finding.recommendation && (
                              <div className="bg-zinc-950 p-2.5 rounded-lg border border-zinc-800/80 text-xxs text-zinc-400 mt-2">
                                <span className="text-indigo-400 font-bold">Fix: </span>
                                {finding.recommendation}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

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
            <span className="font-bold text-zinc-400">DevLens Platform</span>
            <span>|</span>
            <span className="text-violet-400">Phase 4 Gemini AI Intelligence Layer</span>
          </div>
          <div>
            Advisory Notice: AI analysis and recommendations are advisory and should be validated by human engineering teams.
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
