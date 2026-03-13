import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import ForeignKey, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from starlette.middleware.sessions import SessionMiddleware

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://codex_app:codex_app_pw@127.0.0.1:3306/codex_activity",
)
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-in-production")
PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "260000"))


class Base(DeclarativeBase):
    pass


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    members: Mapped[list["User"]] = relationship(back_populates="organisation")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_pw: Mapped[str] = mapped_column(String(255))
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    organisation: Mapped[Organisation] = relationship(back_populates="members")


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)


def init_database(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    algorithm, iter_count, salt_hex, digest_hex = stored_hash.split("$", 3)
    if algorithm != "pbkdf2_sha256":
        return False
    check_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iter_count),
    )
    return hmac.compare_digest(check_digest.hex(), digest_hex)


def html_page(body: str, title: str = "Codex Activity App") -> str:
    return f"""
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>{title}</title>
        <style>
          body {{
            margin: 0;
            font-family: Inter, Segoe UI, Arial, sans-serif;
            background: linear-gradient(180deg, #f1f5f9, #e2e8f0);
            color: #0f172a;
            min-height: 100vh;
          }}

          .shell {{
            max-width: 900px;
            margin: 2.5rem auto;
            padding: 0 1rem;
          }}

          .card {{
            background: #ffffff;
            border-radius: 14px;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.13);
            padding: 1.5rem;
            border: 1px solid #dbe3ee;
          }}

          h1 {{
            margin: 0 0 0.6rem;
            color: #0b3b6d;
            font-size: 1.7rem;
          }}

          h2 {{
            margin: 0 0 0.75rem;
            font-size: 1.1rem;
            color: #334155;
          }}

          p, li, label {{
            color: #334155;
          }}

          .form-grid {{
            display: grid;
            gap: 0.8rem;
            margin-top: 1rem;
          }}

          input, select, button {{
            font: inherit;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
            padding: 0.65rem 0.75rem;
          }}

          button {{
            border: none;
            background: #0b3b6d;
            color: white;
            cursor: pointer;
            font-weight: 600;
          }}

          button:hover {{ background: #0d4d8f; }}

          .logout {{
            background: #dc2626;
            margin-top: 1rem;
          }}

          .logout:hover {{ background: #b91c1c; }}

          .error {{
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fecaca;
            padding: 0.6rem;
            border-radius: 8px;
          }}

          .row {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 1rem;
          }}

          .members {{
            background: #f8fafc;
            border-radius: 10px;
            border: 1px solid #dde7f3;
            padding: 1rem;
          }}

          a {{
            color: #0d4d8f;
            font-weight: 600;
            text-decoration: none;
          }}

          @media (max-width: 760px) {{
            .row {{ grid-template-columns: 1fr; }}
          }}
        </style>
      </head>
      <body>
        <main class=\"shell\">{body}</main>
      </body>
    </html>
    """


def organisation_options(selected: Optional[str] = None) -> str:
    with SessionLocal() as db:
        orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
    options = []
    for org in orgs:
        marker = " selected" if selected == str(org.id) else ""
        options.append(f"<option value=\"{org.id}\"{marker}>{org.name}</option>")
    return "\n".join(options)


@app.on_event("startup")
def on_startup() -> None:
    init_database(reset=False)


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    org_id = request.session["org_id"]
    with SessionLocal() as db:
        members = db.scalars(select(User).where(User.organisation_id == org_id).order_by(User.email)).all()

    body = f"""
      <section class=\"card\">
        <h1>Organisation: {request.session['org_name']}</h1>
        <p><strong>Welcome {request.session['email']}</strong></p>
        <div class=\"row\">
          <div>
            <h2>Dashboard</h2>
            <p>You are logged in to your organisation workspace.</p>
          </div>
          <aside class=\"members\">
            <h2>Members</h2>
            <ul>
              {''.join(f'<li>{member.email}</li>' for member in members)}
            </ul>
          </aside>
        </div>
        <form method=\"post\" action=\"/logout\">
          <button class=\"logout\" type=\"submit\">Logout</button>
        </form>
      </section>
    """
    return HTMLResponse(html_page(body, title="Organisation Dashboard"))


@app.get("/login", response_class=HTMLResponse)
def login_form(error: str = "") -> HTMLResponse:
    message = f"<p class=\"error\">{error}</p>" if error else ""
    body = f"""
      <section class=\"card\">
        <h1>Business Portal Login</h1>
        <p>Sign in with your account and organisation.</p>
        {message}
        <form class=\"form-grid\" method=\"post\" action=\"/login\">
          <label>Email</label>
          <input type=\"email\" name=\"email\" required />
          <label>Password</label>
          <input type=\"password\" name=\"password\" required />
          <label>Organisation</label>
          <select name=\"organisation_id\" required>
            <option value=\"\" disabled selected>Select organisation</option>
            {organisation_options()}
          </select>
          <button type=\"submit\">Login</button>
        </form>
        <p>Need access? <a href=\"/register\">Create account</a></p>
      </section>
    """
    return HTMLResponse(html_page(body, title="Login"))


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    organisation_id: int = Form(...),
) -> RedirectResponse:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if not user or user.organisation_id != organisation_id or not verify_password(password, user.hashed_pw):
            return RedirectResponse(url="/login?error=Invalid+credentials", status_code=303)
        org_name = user.organisation.name

    request.session.clear()
    request.session["user_id"] = user.id
    request.session["email"] = user.email
    request.session["org_id"] = user.organisation_id
    request.session["org_name"] = org_name
    return RedirectResponse(url="/", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_form(error: str = "") -> HTMLResponse:
    message = f"<p class=\"error\">{error}</p>" if error else ""
    body = f"""
      <section class=\"card\">
        <h1>Create Account</h1>
        {message}
        <form class=\"form-grid\" method=\"post\" action=\"/register\">
          <label>Organisation</label>
          <select name=\"organisation_choice\" required>
            <option value=\"\" disabled selected>Select organisation</option>
            {organisation_options()}
            <option value=\"__new__\">Create new organisation</option>
          </select>
          <label>New organisation name (if creating new)</label>
          <input type=\"text\" name=\"new_organisation_name\" />
          <label>Email</label>
          <input type=\"email\" name=\"email\" required />
          <label>Password</label>
          <input type=\"password\" name=\"password\" minlength=\"8\" required />
          <button type=\"submit\">Create account</button>
        </form>
        <p>Already registered? <a href=\"/login\">Back to login</a></p>
      </section>
    """
    return HTMLResponse(html_page(body, title="Create Account"))


@app.post("/register")
def register(
    email: str = Form(...),
    password: str = Form(...),
    organisation_choice: str = Form(...),
    new_organisation_name: str = Form(""),
) -> RedirectResponse:
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            return RedirectResponse(url="/register?error=Email+already+exists", status_code=303)

        if organisation_choice == "__new__":
            org_name = new_organisation_name.strip()
            if not org_name:
                return RedirectResponse(url="/register?error=Provide+new+organisation+name", status_code=303)
            organisation = db.scalar(select(Organisation).where(Organisation.name == org_name))
            if organisation is None:
                organisation = Organisation(name=org_name)
                db.add(organisation)
                db.flush()
        else:
            organisation = db.get(Organisation, int(organisation_choice))
            if organisation is None:
                return RedirectResponse(url="/register?error=Choose+a+valid+organisation", status_code=303)

        user = User(email=email, hashed_pw=hash_password(password), organisation_id=organisation.id)
        db.add(user)
        db.commit()

    return RedirectResponse(url="/login", status_code=303)


@app.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


if __name__ == "__main__":
    reset = os.getenv("RESET_DB", "false").lower() == "true"
    init_database(reset=reset)
