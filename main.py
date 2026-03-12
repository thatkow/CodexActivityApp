import argparse
import os
from typing import Generator

from fastapi import Depends, FastAPI, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import ForeignKey, String, create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from starlette.middleware.sessions import SessionMiddleware


MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DB", "codex_activity_app")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-in-production")

SERVER_DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}"
APP_DATABASE_URL = f"{SERVER_DATABASE_URL}/{MYSQL_DB}"

app = FastAPI(title="Codex Activity App")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Base(DeclarativeBase):
    pass


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    users: Mapped[list["User"]] = relationship(back_populates="organisation")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_pw: Mapped[str] = mapped_column(String(255))
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    organisation: Mapped[Organisation] = relationship(back_populates="users")


engine = create_engine(APP_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def ensure_database_exists() -> None:
    server_engine = create_engine(SERVER_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with server_engine.connect() as connection:
        connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}`"))


def init_db() -> None:
    ensure_database_exists()
    Base.metadata.create_all(bind=engine)


def reset_db() -> None:
    ensure_database_exists()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    members = db.scalars(
        select(User).where(User.organisation_id == user.organisation_id).order_by(User.email.asc())
    ).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "organisation": user.organisation,
            "user": user,
            "members": members,
        },
    )


@app.get("/login")
def login_form(request: Request, db: Session = Depends(get_db)):
    organisations = db.scalars(select(Organisation).order_by(Organisation.name.asc())).all()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "organisations": organisations, "error": None},
    )


@app.post("/login")
def login(
    request: Request,
    organisation_id: int = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.email == email.strip().lower(),
            User.organisation_id == organisation_id,
        )
    )

    if not user or not pwd_context.verify(password, user.hashed_pw):
        organisations = db.scalars(select(Organisation).order_by(Organisation.name.asc())).all()
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "organisations": organisations,
                "error": "Invalid credentials or organisation.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/signup")
def signup_form(request: Request, db: Session = Depends(get_db)):
    organisations = db.scalars(select(Organisation).order_by(Organisation.name.asc())).all()
    return templates.TemplateResponse(
        "signup.html",
        {"request": request, "organisations": organisations, "error": None},
    )


@app.post("/signup")
def signup(
    request: Request,
    organisation_id: str = Form(""),
    new_organisation: str = Form(""),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    selected_org = None
    new_organisation = new_organisation.strip()

    if organisation_id and organisation_id != "new":
        selected_org = db.get(Organisation, int(organisation_id))

    if organisation_id == "new" or not selected_org:
        if not new_organisation:
            organisations = db.scalars(select(Organisation).order_by(Organisation.name.asc())).all()
            return templates.TemplateResponse(
                "signup.html",
                {
                    "request": request,
                    "organisations": organisations,
                    "error": "Choose an organisation or provide a new organisation name.",
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        selected_org = db.scalar(select(Organisation).where(Organisation.name == new_organisation))
        if not selected_org:
            selected_org = Organisation(name=new_organisation)
            db.add(selected_org)
            db.flush()

    user = User(
        email=email.strip().lower(),
        hashed_pw=pwd_context.hash(password),
        organisation_id=selected_org.id,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        organisations = db.scalars(select(Organisation).order_by(Organisation.name.asc())).all()
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "organisations": organisations,
                "error": "Email already exists. Please use a different one.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


def main() -> None:
    parser = argparse.ArgumentParser(description="Codex Activity App database utility")
    parser.add_argument("--init-db", action="store_true", help="Create database and tables if missing")
    parser.add_argument("--reset-db", action="store_true", help="Drop and recreate tables")
    args = parser.parse_args()

    if args.reset_db:
        reset_db()
        return

    if args.init_db:
        init_db()


if __name__ == "__main__":
    main()
