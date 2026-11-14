import argparse

import uvicorn

from bola_lab.config import Settings
from bola_lab.migrations import migrate
from bola_lab.seed import seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Local BOLA lab administration")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="Apply versioned SQL migrations")
    seed_parser = commands.add_parser(
        "seed", help="Insert synthetic lab data (explicit lab opt-in)"
    )
    seed_parser.add_argument(
        "--reset", action="store_true", help="DESTROY and replace existing lab data"
    )
    commands.add_parser("serve", help="Start only after verifying settings and schema")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.command == "migrate":
        migrate(settings)
        print("Migrations verified/applied.")
    elif args.command == "seed":
        seed(settings, reset=args.reset)
        print("Synthetic fixture loaded.")
    else:
        from bola_lab.main import create_app

        uvicorn.run(
            create_app(settings), host=settings.bind_host, port=settings.port, access_log=False
        )


if __name__ == "__main__":
    main()
