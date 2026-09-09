import os
from typing import Dict, Any, List
from app.core.config import settings
from app.services.github_service import GitHubService, GitHubNotFoundError, GitHubAPIError
from app.analyzers.language_detector import detect_language
from app.analyzers.file_classifier import classify_file
from app.analyzers.metrics_analyzer import calculate_metrics
from app.analyzers.security_analyzer import scan_security
from app.analyzers.code_quality_analyzer import scan_quality

async def analyze_repository(
    owner: str, 
    repo: str, 
    metadata: Dict[str, Any], 
    tree_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Coordinates the full static analysis of a repository.
    
    Args:
        owner: Repository owner.
        repo: Repository name.
        metadata: Repository metadata dictionary.
        tree_items: File tree structure list.
        
    Returns:
        A dictionary matching the AnalysisReport schema.
    """
    github_service = GitHubService()
    default_branch = metadata.get("default_branch", "main")
    
    # 1. Classify all files and accumulate summary statistics
    total_files = len(tree_items)
    category_counts = {
        "source": 0,
        "test": 0,
        "documentation": 0,
        "configuration": 0,
        "asset": 0,
        "unknown": 0
    }
    
    eligible_files = []
    
    for item in tree_items:
        path = item["path"]
        category = classify_file(path)
        category_counts[category] += 1
        
        # We only analyze source code and test files for metrics and quality findings
        if category in ("source", "test"):
            eligible_files.append((path, category))

    # 2. Iterate eligible files and enforce limits
    analyzed_files_list = []
    findings = []
    fetched_contents: Dict[str, str] = {}
    
    skipped_count = 0
    skip_reasons = {
        "too_large": 0,
        "unsupported": 0,
        "limit_exceeded": 0
    }
    
    total_content_bytes = 0
    files_analyzed_count = 0
    
    # Sort files alphabetically to ensure deterministic evaluation
    eligible_files.sort(key=lambda x: x[0])
    
    for path, category in eligible_files:
        # Check limit: Maximum files analyzed
        if files_analyzed_count >= settings.MAX_FILES_ANALYZED:
            skipped_count += 1
            skip_reasons["limit_exceeded"] += 1
            continue
            
        try:
            # Fetch raw content
            content = await github_service.get_file_content(owner, repo, path, default_branch)
            
            # Check content size limit
            content_bytes = content.encode("utf-8")
            size_bytes = len(content_bytes)
            
            if size_bytes > settings.MAX_FILE_SIZE_BYTES:
                skipped_count += 1
                skip_reasons["too_large"] += 1
                continue
                
            # Check total accumulated content bytes limit
            if total_content_bytes + size_bytes > settings.MAX_TOTAL_CONTENT_BYTES:
                skipped_count += 1
                skip_reasons["limit_exceeded"] += 1
                continue
                
            # Check for binary file content (rough check looking for null bytes)
            if "\x00" in content:
                skipped_count += 1
                skip_reasons["unsupported"] += 1
                continue
                
        except (GitHubNotFoundError, GitHubAPIError, Exception):
            # If a file fails to load, count as skipped/unsupported
            skipped_count += 1
            skip_reasons["unsupported"] += 1
            continue
            
        # Analysis phase
        lang = detect_language(path)
        
        # Calculate line metrics
        tot_lines, blk_lines, cmt_lines, code_lines = calculate_metrics(content, lang)
        
        # Collect findings
        file_findings = []
        file_findings.extend(scan_security(content, path))
        file_findings.extend(scan_quality(content, path, lang))
        findings.extend(file_findings)
        
        # Record file metrics
        file_metric = {
            "path": path,
            "language": lang,
            "category": category,
            "size_bytes": size_bytes,
            "line_count": tot_lines,
            "code_lines": code_lines,
            "comment_lines": cmt_lines,
            "blank_lines": blk_lines
        }
        
        analyzed_files_list.append(file_metric)
        fetched_contents[path] = content
        
        # Accumulate metrics
        total_content_bytes += size_bytes
        files_analyzed_count += 1

    # 3. Calculate aggregate repository-wide metrics
    repo_tot_lines = sum(f["line_count"] for f in analyzed_files_list)
    repo_code_lines = sum(f["code_lines"] for f in analyzed_files_list)
    repo_comment_lines = sum(f["comment_lines"] for f in analyzed_files_list)
    repo_blank_lines = sum(f["blank_lines"] for f in analyzed_files_list)
    
    # Sort files to find largest
    largest_by_size = sorted(
        [{"path": f["path"], "size_bytes": f["size_bytes"]} for f in analyzed_files_list],
        key=lambda x: x["size_bytes"],
        reverse=True
    )[:5]
    
    largest_by_lines = sorted(
        [{"path": f["path"], "line_count": f["line_count"]} for f in analyzed_files_list],
        key=lambda x: x["line_count"],
        reverse=True
    )[:5]
    
    repo_metrics = {
        "total_lines": repo_tot_lines,
        "code_lines": repo_code_lines,
        "comment_lines": repo_comment_lines,
        "blank_lines": repo_blank_lines,
        "largest_files_by_size": largest_by_size,
        "largest_files_by_lines": largest_by_lines
    }

    # 4. Calculate language distribution
    lang_counts = {}
    for f in analyzed_files_list:
        lang = f["language"]
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        
    languages_dist = []
    total_lang_files = len(analyzed_files_list)
    
    # Sort languages alphabetically for deterministic reports
    for lang in sorted(lang_counts.keys()):
        count = lang_counts[lang]
        pct = round((count / total_lang_files) * 100, 2) if total_lang_files > 0 else 0.0
        languages_dist.append({
            "language": lang,
            "file_count": count,
            "percentage": pct
        })
        
    # Sort by percentage desc
    languages_dist.sort(key=lambda x: x["percentage"], reverse=True)

    # 5. Format results into structured dictionary matching schemas
    summary = {
        "total_files": total_files,
        "analyzed_files": files_analyzed_count,
        "skipped_files": skipped_count,
        "source_files": category_counts["source"],
        "test_files": category_counts["test"],
        "documentation_files": category_counts["documentation"],
        "configuration_files": category_counts["configuration"],
        "asset_files": category_counts["asset"],
        "unknown_files": category_counts["unknown"]
    }
    
    analysis_metadata = {
        "files_analyzed": files_analyzed_count,
        "files_skipped": skipped_count,
        "skip_reasons": skip_reasons
    }

    return {
        "repository": {
            "owner": metadata["owner"],
            "name": metadata["name"],
            "full_name": metadata["full_name"],
            "description": metadata["description"],
            "default_branch": metadata["default_branch"],
            "language": metadata.get("language"),
            "stars": metadata["stars"],
            "forks": metadata["forks"],
            "open_issues": metadata["open_issues"],
            "url": metadata["url"]
        },
        "summary": summary,
        "languages": languages_dist,
        "files": analyzed_files_list,
        "metrics": repo_metrics,
        "findings": findings,
        "analysis_metadata": analysis_metadata,
        "tree": [
            {
                "path": item["path"],
                "type": item["type"]
            }
            for item in tree_items
        ],
        "file_contents": fetched_contents
    }
