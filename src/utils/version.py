"""Unified versioning: always 1.0.0.<short_commit_hash>"""
import subprocess
import os

BASE_VERSION = "1.0.2"

def _get_git_commit_hash():
    """Return short commit hash or 'unknown' if not a git repo."""
    try:
        # Try environment first (CI systems often expose this)
        for env_var in ("GITHUB_SHA", "CI_COMMIT_SHA"):
            if env_var in os.environ and os.environ[env_var]:
                return os.environ[env_var][:8]
        # Fallback to git command
        result = subprocess.run([
            'git','rev-parse','--short','HEAD'
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return "unknown"

def get_version_string():
    commit = _get_git_commit_hash()
    return f"{BASE_VERSION}.{commit}" if commit != "unknown" else f"{BASE_VERSION}"

def get_full_version_info():
    commit = _get_git_commit_hash()
    return f"Wersja: {get_version_string()}"

APP_VERSION = get_version_string()
