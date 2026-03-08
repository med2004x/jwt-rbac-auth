from pathlib import Path
import os

import psycopg


def main() -> None:
    migration_directory = Path("/service/src/migrations")
    database_url = os.environ["MIGRATION_DATABASE_URL"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            for migration_path in sorted(migration_directory.glob("*.sql")):
                cursor.execute(migration_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
