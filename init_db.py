import argparse
import os

import mysql.connector


def server_config() -> dict[str, str | int]:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "codex_app"),
        "password": os.getenv("DB_PASSWORD", "codex_password"),
    }


def db_name() -> str:
    return os.getenv("DB_NAME", "codex_activity_app")


def init_database(recreate: bool) -> None:
    config = server_config()
    database = db_name()

    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}`")
        cursor.execute(f"USE `{database}`")

        if recreate:
            cursor.execute("DROP TABLE IF EXISTS projects")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                date_created DATE NOT NULL
            ) ENGINE=InnoDB
            """
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the MySQL schema.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the projects table before creating schema.",
    )
    args = parser.parse_args()
    init_database(recreate=args.recreate)


if __name__ == "__main__":
    main()
