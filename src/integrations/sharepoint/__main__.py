"""CLI: test połączenia z SharePoint (tylko odczyt).

    python -m src.integrations.sharepoint --env DEV
    python -m src.integrations.sharepoint --env PROD
"""
import argparse
import sys

from .config import DEFAULT_ENV, ENVIRONMENTS, EnvironmentConfigError
from .connection_test import run_readonly_test
from .environment import environment_manager


def main(argv=None):
    parser = argparse.ArgumentParser(description="Test połączenia z SharePoint (tylko odczyt).")
    parser.add_argument(
        "--env",
        default=DEFAULT_ENV,
        choices=list(ENVIRONMENTS),
        type=str.upper,
        help=f"Środowisko (domyślnie {DEFAULT_ENV}). PROD należy wskazać jawnie.",
    )
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        env = environment_manager.set_active(args.env)
    except EnvironmentConfigError as e:
        print(f"[BŁĄD] {e}")
        return 2

    report = run_readonly_test(env, log=print)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
