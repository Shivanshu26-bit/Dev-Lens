export interface RepositoryMetadata {
  owner: string;
  name: string;
  full_name: string;
  description: string | null;
  default_branch: string;
  language: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  url: string;
}

export interface TreeItem {
  path: string;
  type: 'file' | 'directory';
}

export interface AnalyzeResponse {
  repository: RepositoryMetadata;
  tree: TreeItem[];
}

// Phase 3 Deep Analysis Report Interfaces
export interface AnalysisSummary {
  total_files: number;
  analyzed_files: number;
  skipped_files: number;
  source_files: number;
  test_files: number;
  documentation_files: number;
  configuration_files: number;
  asset_files: number;
  unknown_files: number;
}

export interface LanguageDistribution {
  language: string;
  file_count: number;
  percentage: number;
}

export interface FileMetrics {
  path: string;
  language: string;
  category: string;
  size_bytes: number;
  line_count: number;
  code_lines: number;
  comment_lines: number;
  blank_lines: number;
}

export interface SizeMetric {
  path: string;
  size_bytes: number;
}

export interface LinesMetric {
  path: string;
  line_count: number;
}

export interface RepoMetrics {
  total_lines: number;
  code_lines: number;
  comment_lines: number;
  blank_lines: number;
  largest_files_by_size: SizeMetric[];
  largest_files_by_lines: LinesMetric[];
}

export interface Finding {
  id: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  category: string;
  title: string;
  description: string;
  file: string;
  line: number;
  recommendation: string;
}

export interface SkipReasons {
  too_large: number;
  unsupported: number;
  limit_exceeded: number;
}

export interface AnalysisMetadata {
  files_analyzed: number;
  files_skipped: number;
  skip_reasons: SkipReasons;
}

export interface AnalysisReport {
  repository: RepositoryMetadata;
  summary: AnalysisSummary;
  languages: LanguageDistribution[];
  files: FileMetrics[];
  metrics: RepoMetrics;
  findings: Finding[];
  analysis_metadata: AnalysisMetadata;
  tree: TreeItem[];
}

// Phase 4 AI Intelligence Layer Interfaces
export type AssessmentRating = 'excellent' | 'good' | 'fair' | 'needs_attention' | 'poor';
export type PriorityLevel = 'critical' | 'high' | 'medium' | 'low';
export type ConfidenceLevel = 'high' | 'medium' | 'low';

export interface ArchitectureAssessment {
  rating: AssessmentRating;
  assessment: string;
  strengths: string[];
  weaknesses: string[];
}

export interface SecurityAssessment {
  rating: AssessmentRating;
  assessment: string;
  strengths: string[];
  weaknesses: string[];
  important_issues: string[];
  recommendations: string[];
}

export interface PerformanceAssessment {
  rating: AssessmentRating;
  assessment: string;
  recommendations: string[];
}

export interface MaintainabilityAssessment {
  rating: AssessmentRating;
  assessment: string;
  recommendations: string[];
}

export interface DocumentationAssessment {
  rating: AssessmentRating;
  assessment: string;
  recommendations: string[];
}

export interface PriorityRecommendation {
  priority: PriorityLevel;
  category: string;
  title: string;
  explanation: string;
  recommendation: string;
  evidence: string;
}

export interface AIAnalysisReport {
  executive_summary: string;
  architecture: ArchitectureAssessment;
  security: SecurityAssessment;
  performance: PerformanceAssessment;
  maintainability: MaintainabilityAssessment;
  documentation: DocumentationAssessment;
  strengths: string[];
  priorities: PriorityRecommendation[];
  confidence: ConfidenceLevel;
  confidence_reason?: string | null;
}

export interface AIAnalyzeResponse {
  repository: RepositoryMetadata;
  deterministic_analysis: AnalysisReport;
  ai_analysis: AIAnalysisReport;
}

export interface User {
  id: string;
  github_user_id: string;
  github_login: string;
  name: string | null;
  email: string | null;
  avatar_url: string | null;
  created_at: string;
}

// Phase 6A Repository History Interfaces
export interface LatestAnalysisSummary {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  analysis_type: 'deterministic' | 'ai' | 'full';
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  total_lines: number | null;
  code_lines: number | null;
  total_files: number | null;
  findings_count: number | null;
}

export interface RepositoryListItem {
  id: string;
  github_url: string;
  owner: string;
  name: string;
  default_branch: string;
  description: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  language: string | null;
  is_private: boolean;
  created_at: string;
  updated_at: string;
  last_analyzed_at: string | null;
  latest_analysis: LatestAnalysisSummary | null;
}

export interface AnalysisRunSummary {
  id: string;
  repository_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  analysis_type: 'deterministic' | 'ai' | 'full';
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface AnalysisRunDetail extends AnalysisRunSummary {
  deterministic_result: AnalysisReport | null;
  ai_result: AIAnalysisReport | null;
  metrics: RepoMetrics | null;
  findings: Finding[] | null;
  languages: LanguageDistribution[] | null;
  metadata_json: Record<string, any> | null;
}
