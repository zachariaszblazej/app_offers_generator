"""
OS utilities

Provides a helper to open documents in the system's associated application.
On macOS, it prefers Microsoft Word when available for .docx files.
"""
import os
import sys
import subprocess


def open_document(file_path: str) -> None:
    """Open a document with the default app (preferring Word on macOS).

    Best-effort: errors are swallowed and printed to console.
    """
    if not file_path:
        return
    try:
        # Ensure path is absolute for safety
        path = os.path.abspath(file_path)
        if sys.platform == "darwin":
            # Try to open specifically with Microsoft Word; fall back to default
            try:
                subprocess.run(["open", "-a", "Microsoft Word", path], check=False)
            except Exception:
                subprocess.run(["open", path], check=False)
        elif os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception as e:
        print(f"Could not open document '{file_path}': {e}")
