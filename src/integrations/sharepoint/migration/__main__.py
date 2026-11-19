"""CLI migratora SQLite -> SharePoint DEV.

    python -m src.integrations.sharepoint.migration                  # dry-run (domyślnie)
    python -m src.integrations.sharepoint.migration --execute --confirm MIGRATE-DEV

Brak opcji wyboru środowiska: migrator działa wyłącznie w DEV.
"""
import argparse
import sys

from .datadir import DataDirError, resolve_data_dir
from .guard import MigrationGuardError
from .runner import CONFIRM_PHRASE, MigrationRefused, run_dry_run, run_execute, save_report
from .report import render_text
from .source import SourceError
from .synthetic_test import CONFIRM_SYNTHETIC, render_text as render_synthetic, run_synthetic_test
from .writer import WriteError
from src.integrations.sharepoint.graph_client import AuthError, GraphError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Migracja SQLite -> listy SharePoint DEV (domyślnie dry-run).")
    parser.add_argument("--db", help="Ścieżka do bazy SQLite (domyślnie z ustawień aplikacji).")
    parser.add_argument("--report-dir", help="Katalog raportów i mapy ID (domyślnie %%APPDATA%%\\HantechDokumenty\\migration).")
    parser.add_argument("--execute", action="store_true", help="Wykonaj zapis do DEV (wymaga --lists i --confirm).")
    parser.add_argument("--lists", default="", help="Listy etapu, np. Suppliers,Clients (wymagane przy --execute).")
    parser.add_argument("--confirm", default="", help=f"Fraza potwierdzająca zapis: {CONFIRM_PHRASE}")
    parser.add_argument("--allow-errors", action="store_true", help="Przy --execute pomiń rekordy błędne zamiast odmówić.")
    parser.add_argument("--synthetic-test", action="store_true",
                        help="Test zapisu: jeden syntetyczny rekord w Clients (utwórz, odczytaj, usuń). "
                             f"Wymaga --confirm {CONFIRM_SYNTHETIC}.")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        report_dir = resolve_data_dir(args.report_dir)  # odmowa dla katalogów w repozytorium - przed jakąkolwiek pracą
        if args.synthetic_test:
            report = run_synthetic_test(args.confirm, report_dir=report_dir)
            print(render_synthetic(report))
            print(f"\nRaport zapisano: {report['_plik']}.txt / .json")
            return 0 if report["wynik"] == "UDANY" else 1
        if args.execute:
            report = run_execute(args.confirm, lists=args.lists, db_path=args.db, report_dir=report_dir,
                                 allow_errors=args.allow_errors)
            prefix = "execute"
        else:
            report = run_dry_run(db_path=args.db, report_dir=report_dir)
            prefix = "dryrun"
    except MigrationGuardError as e:
        print(f"[ZABLOKOWANO] {e}")
        return 3
    except MigrationRefused as e:
        print(f"[ODMOWA] {e}")
        return 4
    except DataDirError as e:
        print(f"[ODMOWA] {e}")
        return 4
    except ValueError as e:
        print(f"[ODMOWA] {e}")
        return 4
    except (SourceError, AuthError, GraphError, WriteError) as e:
        print(f"[BŁĄD] {e}")
        return 1

    base = save_report(report, report_dir, prefix)
    print(render_text(report))
    print(f"\nRaport zapisano: {base}.txt / .json")
    if report.get("wykonanie") and not report["wykonanie"]["ok"]:
        return 1
    if not report["zrodlo"]["niezmienione"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
