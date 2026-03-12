import os
from typing import Generator, Optional

from fastapi import Depends, FastAPI, Form, Request, status
from fastapi.middleware import Middleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from starlette.middleware.sessions import SessionMiddleware


def _database_url() -> str:
    user = os.getenv("DB_USER", "codexapp")
    password = os.getenv("DB_PASSWORD", "codexpass")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "codex_activity")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = os.getenv("DATABASE_URL", _database_url())
SECRET_KEY = os.getenv("SESSION_SECRET", "change-me-in-production")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, nullable=False)
    users = relationship("User", back_populates="organisation", cascade="all, delete")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_user_email_org"),)

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    organization_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)

    organisation = relationship("Organisation", back_populates="users")


middleware = [Middleware(SessionMiddleware, secret_key=SECRET_KEY)]
app = FastAPI(middleware=middleware)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(request: Request, db: Session) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user:
        members = (
            db.query(User)
            .filter(User.organization_id == user.organization_id)
            .order_by(User.email.asc())
            .all()
        )
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,
                "organisation": user.organisation,
                "members": members,
            },
        )

    organisations = db.query(Organisation).order_by(Organisation.name.asc()).all()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "organisations": organisations, "error": request.query_params.get("error")},
    )


@app.post("/login")
def login(
    request: Request,
    organization_id: int = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.organization_id == organization_id, User.email == email.strip().lower())
        .first()
    )
    if not user or not pwd_context.verify(password, user.password_hash):
        return RedirectResponse(url="/?error=Invalid+credentials", status_code=status.HTTP_303_SEE_OTHER)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/register")
def register_form(request: Request, db: Session = Depends(get_db)):
    organisations = db.query(Organisation).order_by(Organisation.name.asc()).all()
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "organisations": organisations, "error": request.query_params.get("error")},
    )


@app.post("/register")
def register(
    organization_id: Optional[int] = Form(None),
    new_organization: Optional[str] = Form(None),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    org = None
    new_organization = (new_organization or "").strip()

    if new_organization:
        existing = db.query(Organisation).filter(Organisation.name == new_organization).first()
        if existing:
            org = existing
        else:
            org = Organisation(name=new_organization)
            db.add(org)
            db.flush()
    elif organization_id:
        org = db.query(Organisation).filter(Organisation.id == organization_id).first()

    if not org:
        return RedirectResponse(url="/register?error=Select+or+create+an+organisation", status_code=status.HTTP_303_SEE_OTHER)

    normalized_email = email.strip().lower()
    existing_user = (
        db.query(User)
        .filter(User.organization_id == org.id, User.email == normalized_email)
        .first()
    )
    if existing_user:
        return RedirectResponse(url="/register?error=User+already+exists+for+that+organisation", status_code=status.HTTP_303_SEE_OTHER)

    user = User(
        email=normalized_email,
        password_hash=pwd_context.hash(password),
        organization_id=org.id,
    )
    db.add(user)
    db.commit()

    return RedirectResponse(url="/?error=Account+created.+Please+log+in", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
