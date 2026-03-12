import argparse

from main import Base, engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize database schema")
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate all tables")
    args = parser.parse_args()

    if args.recreate:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
