import argparse
import os

import pymysql

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "codex_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "codex_app_password")
DB_NAME = os.getenv("DB_NAME", "codex_activity_app")


def conn(database=None):
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,
        autocommit=True,
    )


def init_db(recreate: bool = False) -> None:
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")

    with conn(DB_NAME) as c:
        with c.cursor() as cur:
            if recreate:
                cur.execute("DROP TABLE IF EXISTS project_members")
                cur.execute("DROP TABLE IF EXISTS members")
                cur.execute("DROP TABLE IF EXISTS projects")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    date_created DATE NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS members (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    first_name VARCHAR(120) NOT NULL,
                    middle_name VARCHAR(120) NULL,
                    last_name VARCHAR(120) NOT NULL,
                    phone VARCHAR(30) NULL,
                    email VARCHAR(255) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS project_members (
                    project_id INT NOT NULL,
                    member_id INT NOT NULL,
                    PRIMARY KEY (project_id, member_id),
                    CONSTRAINT fk_pm_project FOREIGN KEY (project_id)
                      REFERENCES projects(id) ON DELETE CASCADE,
                    CONSTRAINT fk_pm_member FOREIGN KEY (member_id)
                      REFERENCES members(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize CodexActivityApp MySQL database")
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate tables")
    args = parser.parse_args()
    init_db(recreate=args.recreate)
    print("Database initialized.")
