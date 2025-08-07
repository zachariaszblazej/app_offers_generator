"""
Version and build information for the application
"""
import os
import json
from datetime import datetime

# Default version info (will be overridden by build process)
DEFAULT_VERSION_INFO = {
    "version": "2.1.0",
    "build_number": "dev",
    "commit_hash": "unknown",
    "build_date": "development",
    "branch": "local",
    "github_run_id": None,
    "github_run_number": None
}

def get_version_info():
    """Get version information from build file or return defaults"""
    try:
        # Try to read build info from generated file
        build_info_path = os.path.join(os.path.dirname(__file__), '..', '..', 'build_info.json')
        if os.path.exists(build_info_path):
            with open(build_info_path, 'r', encoding='utf-8') as f:
                build_info = json.load(f)
                return build_info
    except Exception as e:
        print(f"Could not read build info: {e}")
    
    # Fallback to default version info
    return DEFAULT_VERSION_INFO

def get_version_string():
    """Get formatted version string for display"""
    info = get_version_info()
    
    if info["build_number"] == "dev":
        return f"v{info['version']} (Development)"
    elif info["github_run_number"]:
        return f"v{info['version']} (Build #{info['github_run_number']})"
    else:
        return f"v{info['version']} (Build {info['build_number']})"

def get_full_version_info():
    """Get detailed version information for about dialog"""
    info = get_version_info()
    
    lines = [
        f"Wersja: {info['version']}",
    ]
    
    if info["build_number"] != "dev":
        lines.append(f"Build: {info['build_number']}")
    
    if info["github_run_number"]:
        lines.append(f"GitHub Build: #{info['github_run_number']}")
        
    if info["commit_hash"] != "unknown":
        short_hash = info["commit_hash"][:8] if len(info["commit_hash"]) > 8 else info["commit_hash"]
        lines.append(f"Commit: {short_hash}")
    
    if info["branch"] != "local":
        lines.append(f"Branch: {info['branch']}")
        
    if info["build_date"] != "development":
        lines.append(f"Data buildu: {info['build_date']}")
    
    return "\n".join(lines)

# Export the current version for backward compatibility
APP_VERSION = get_version_string()
