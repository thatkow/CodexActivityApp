import base64
import hashlib
import hmac
import os
import secrets
from typing import Generator
import html

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import ForeignKey, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship(back_populates="organisation")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_pw: Mapped[str] = mapped_column(String(255), nullable=False)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    organisation: Mapped[Organisation] = relationship(back_populates="users")


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://codex_app:codex_app_password@127.0.0.1:3306/codex_activity_app",
)
SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-this-in-production")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

app = FastAPI(title="Codex Activity App")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256$120000${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    algorithm, iterations, salt_b64, hash_b64 = encoded.split("$", 3)
    if algorithm != "pbkdf2_sha256":
        return False
    salt = base64.b64decode(salt_b64.encode())
    expected = base64.b64decode(hash_b64.encode())
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(check, expected)


def sign_session_value(user_id: int) -> str:
    raw = str(user_id).encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return f"{user_id}.{sig}"


def parse_session_value(cookie_value: str | None) -> int | None:
    if not cookie_value or "." not in cookie_value:
        return None
    id_str, sig = cookie_value.split(".", 1)
    if not id_str.isdigit():
        return None
    expected = hmac.new(SECRET_KEY.encode("utf-8"), id_str.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return int(id_str)


def page_template(title: str, body: str) -> str:
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
            font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
            background: #eef2f7;
            color: #12263a;
          }}
          .shell {{
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 24px;
          }}
          .card {{
            width: min(900px, 100%);
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 10px 30px rgba(16, 42, 67, 0.12);
            overflow: hidden;
          }}
          .header {{
            background: linear-gradient(100deg, #1f3c88, #2d6cdf);
            color: white;
            padding: 22px 28px;
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: 0.01em;
          }}
          .content {{ padding: 26px 28px 30px; }}
          h1, h2, h3, p {{ margin-top: 0; }}
          label {{ font-size: 0.93rem; font-weight: 600; display: block; margin: 14px 0 6px; }}
          input, select, button {{
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #c4cfdb;
            border-radius: 9px;
            font-size: 0.95rem;
            box-sizing: border-box;
          }}
          button {{
            margin-top: 16px;
            background: #1f3c88;
            color: #fff;
            border: none;
            font-weight: 700;
            cursor: pointer;
          }}
          .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start; }}
          .muted {{ color: #5f6c7b; }}
          .error {{ background: #ffe1e1; color: #8a1717; border-radius: 8px; padding: 10px; margin-bottom: 12px; }}
          .link {{ margin-top: 14px; display: inline-block; color: #1f3c88; text-decoration: none; font-weight: 600; }}
          ul {{ margin: 0; padding-left: 20px; }}
          .top-actions {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 14px; }}
          .logout {{ max-width: 140px; margin: 0; background: #305ca8; }}
          @media (max-width: 768px) {{ .row {{ grid-template-columns: 1fr; }} }}
        </style>
      </head>
      <body>
        <div class=\"shell\">
          <div class=\"card\">{body}</div>
        </div>
      </body>
    </html>
    """


def login_form(org_options: str, error: str = "") -> str:
    error_html = f'<div class="error">{error}</div>' if error else ""
    return page_template(
        "Login",
        f"""
        <div class=\"header\">Business Portal Login</div>
        <div class=\"content\">
          {error_html}
          <form method=\"post\" action=\"/login\">
            <label for=\"organisation_id\">Organisation</label>
            <select id=\"organisation_id\" name=\"organisation_id\" required>
              {org_options}
            </select>

            <label for=\"email\">Email</label>
            <input id=\"email\" name=\"email\" type=\"email\" required />

            <label for=\"password\">Password</label>
            <input id=\"password\" name=\"password\" type=\"password\" required />

            <button type=\"submit\">Login</button>
          </form>
          <a class=\"link\" href=\"/register\">Create account</a>
        </div>
        """,
    )


def register_form(org_options: str, error: str = "") -> str:
    error_html = f'<div class="error">{error}</div>' if error else ""
    return page_template(
        "Create Account",
        f"""
        <div class=\"header\">Create Your Business Account</div>
        <div class=\"content\">
          {error_html}
          <form method=\"post\" action=\"/register\">
            <label for=\"organisation_id\">Organisation</label>
            <select id=\"organisation_id\" name=\"organisation_id\" onchange=\"toggleNewOrg()\" required>
              {org_options}
              <option value=\"new\">+ Create new organisation</option>
            </select>

            <div id=\"new-org-wrap\" style=\"display:none\">
              <label for=\"new_organisation_name\">New organisation name</label>
              <input id=\"new_organisation_name\" name=\"new_organisation_name\" type=\"text\" />
            </div>

            <label for=\"email\">Email</label>
            <input id=\"email\" name=\"email\" type=\"email\" required />

            <label for=\"password\">Password</label>
            <input id=\"password\" name=\"password\" type=\"password\" minlength=\"8\" required />

            <button type=\"submit\">Create Account</button>
          </form>
          <a class=\"link\" href=\"/\">Back to login</a>
        </div>
        <script>
          function toggleNewOrg() {{
            const select = document.getElementById('organisation_id');
            const wrap = document.getElementById('new-org-wrap');
            wrap.style.display = select.value === 'new' ? 'block' : 'none';
          }}
          toggleNewOrg();
        </script>
        """,
    )


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    with SessionLocal() as db:
        user_id = parse_session_value(request.cookies.get("session"))
        if user_id is None:
            orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
            options = "".join([f'<option value="{org.id}">{org.name}</option>' for org in orgs])
            if not options:
                options = '<option value="" disabled selected>No organisations yet - create one</option>'
            return HTMLResponse(login_form(options))

        user = db.get(User, user_id)
        if not user:
            response = RedirectResponse(url="/", status_code=303)
            response.delete_cookie("session")
            return response

        members = db.scalars(
            select(User).where(User.organisation_id == user.organisation_id).order_by(User.email)
        ).all()

        member_items = "".join(f"<li>{html.escape(member.email)}</li>" for member in members)
        return HTMLResponse(
            page_template(
                "Dashboard",
                f"""
                <div class=\"header\">Organisation: {html.escape(user.organisation.name)} </div>
                <div class=\"content\">
                  <div class=\"top-actions\">
                    <div>
                      <h2>Welcome {html.escape(user.email)}</h2>
                      <p class=\"muted\">Logged into your organisation workspace.</p>
                    </div>
                    <form method=\"post\" action=\"/logout\" style=\"margin:0\">
                      <button type=\"submit\" class=\"logout\">Logout</button>
                    </form>
                  </div>
                  <h3>Members</h3>
                  <ul>{member_items}</ul>
                </div>
                """,
            )
        )


@app.post("/login", response_model=None)
def login(email: str = Form(...), password: str = Form(...), organisation_id: int = Form(...)) -> HTMLResponse | RedirectResponse:
    with SessionLocal() as db:
        orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
        options = "".join([f'<option value="{org.id}">{org.name}</option>' for org in orgs])
        user = db.scalar(
            select(User).where(User.email == email.strip().lower(), User.organisation_id == organisation_id)
        )
        if not user or not verify_password(password, user.hashed_pw):
            return HTMLResponse(login_form(options, "Invalid credentials or organisation selection."), status_code=400)

        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie("session", sign_session_value(user.id), httponly=True, samesite="lax")
        return response


@app.get("/register", response_class=HTMLResponse)
def register_page() -> HTMLResponse:
    with SessionLocal() as db:
        orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
        options = "".join([f'<option value="{org.id}">{org.name}</option>' for org in orgs])
        return HTMLResponse(register_form(options))


@app.post("/register", response_model=None)
def register(
    email: str = Form(...),
    password: str = Form(...),
    organisation_id: str = Form(...),
    new_organisation_name: str = Form(""),
) -> HTMLResponse | RedirectResponse:
    normalized_email = email.strip().lower()
    if len(password) < 8:
        with SessionLocal() as db:
            orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
            options = "".join([f'<option value="{org.id}">{org.name}</option>' for org in orgs])
            return HTMLResponse(register_form(options, "Password must be at least 8 characters."), status_code=400)

    with SessionLocal() as db:
        orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
        options = "".join([f'<option value="{org.id}">{org.name}</option>' for org in orgs])

        existing = db.scalar(select(User).where(User.email == normalized_email))
        if existing:
            return HTMLResponse(register_form(options, "Email is already in use."), status_code=400)

        if organisation_id == "new":
            org_name = new_organisation_name.strip()
            if not org_name:
                return HTMLResponse(register_form(options, "Enter a name for the new organisation."), status_code=400)

            org = db.scalar(select(Organisation).where(Organisation.name == org_name))
            if not org:
                org = Organisation(name=org_name)
                db.add(org)
                db.flush()
        else:
            if not organisation_id.isdigit():
                return HTMLResponse(register_form(options, "Invalid organisation selection."), status_code=400)
            org = db.get(Organisation, int(organisation_id))
            if not org:
                return HTMLResponse(register_form(options, "Selected organisation does not exist."), status_code=400)

        user = User(email=normalized_email, hashed_pw=hash_password(password), organisation_id=org.id)
        db.add(user)
        db.commit()
        db.refresh(user)

        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie("session", sign_session_value(user.id), httponly=True, samesite="lax")
        return response


@app.post("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session")
    return response
