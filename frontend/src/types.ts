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
