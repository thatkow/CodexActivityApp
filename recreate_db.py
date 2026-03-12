import os

from sqlalchemy import create_engine

from app import Base


DB_USER = os.getenv("DB_USER", "codex_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "codex_password")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "codex_activity")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)


def recreate_database() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    recreate_database()
    print("Database recreated.")
