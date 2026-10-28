"""Point d'entrée en ligne de commande.

python -m jobmarket run [--date AAAA-MM-JJ] [--refresh]
python -m jobmarket serve [--cron "0 7 * * *"]
python -m jobmarket report
"""

from __future__ import annotations

import argparse
from datetime import date

from jobmarket.flow import jobmarket_flow


def main() -> None:
    parser = argparse.ArgumentParser(prog="jobmarket", description="Pipeline des offres data France Travail")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Exécute le pipeline une fois")
    run.add_argument("--date", type=date.fromisoformat, help="Date d'ingestion à produire ou rejouer")
    run.add_argument("--refresh", action="store_true", help="Rappelle l'API même si les données du jour existent")

    serve = sub.add_parser("serve", help="Planifie le pipeline (nécessite un serveur Prefect)")
    serve.add_argument("--cron", default="0 7 * * *", help="Planification cron (par défaut tous les jours à 7 h)")

    sub.add_parser("report", help="Affiche un résumé de la table des offres")

    args = parser.parse_args()
    if args.command == "run":
        jobmarket_flow(ingestion_date=args.date, refresh=args.refresh)
    elif args.command == "serve":
        jobmarket_flow.serve(name="quotidien", cron=args.cron)
    else:
        from jobmarket.report import print_report

        print_report()


if __name__ == "__main__":
    main()
