import os
from html import escape

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from sqlalchemy import ForeignKey, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from starlette.middleware.sessions import SessionMiddleware


class Base(DeclarativeBase):
    pass


class Organisation(Base):
    __tablename__ = "organisation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    members: Mapped[list["User"]] = relationship(back_populates="organisation", cascade="all,delete")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_pw: Mapped[str] = mapped_column(String(255), nullable=False)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisation.id"), nullable=False)
    organisation: Mapped[Organisation] = relationship(back_populates="members")


DATABASE_URL = os.getenv(
    "DATABASE_URL", "mysql+pymysql://codex_app:codex_app_password@127.0.0.1:3306/codex_activity_app"
)
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-in-production")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Codex Activity App")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)


def reset_database() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def ensure_database() -> None:
    Base.metadata.create_all(engine)


def render_shell(title: str, body: str) -> str:
    return f"""
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>{escape(title)}</title>
        <style>
          :root {{
            --bg: #eef3f8;
            --card: #ffffff;
            --primary: #16447b;
            --accent: #2878d6;
            --text: #1e293b;
            --muted: #6b7280;
            --border: #d8e0eb;
          }}
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            min-height: 100vh;
            font-family: "Inter", "Segoe UI", Arial, sans-serif;
            background: linear-gradient(180deg, #e9f0f8 0%, #f8fbff 100%);
            color: var(--text);
          }}
          .topbar {{
            background: linear-gradient(90deg, #0f2744, #1e4d81);
            color: #fff;
            padding: 1rem 2rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            box-shadow: 0 3px 14px rgba(15, 39, 68, 0.3);
          }}
          .layout {{
            max-width: 980px;
            margin: 2rem auto;
            padding: 0 1rem;
          }}
          .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            box-shadow: 0 14px 30px rgba(15, 39, 68, 0.08);
            padding: 1.5rem;
          }}
          h1, h2, h3 {{ margin-top: 0; }}
          .subtle {{ color: var(--muted); }}
          .form-grid {{ display: grid; gap: 0.8rem; margin-top: 1rem; }}
          label {{ font-weight: 600; font-size: 0.92rem; }}
          input, select {{
            width: 100%;
            padding: 0.65rem 0.75rem;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 0.95rem;
          }}
          button {{
            margin-top: 0.5rem;
            background: var(--accent);
            color: white;
            border: 0;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 600;
            padding: 0.72rem 1.1rem;
            cursor: pointer;
          }}
          .link {{ margin-top: 1rem; display: inline-block; color: #1e4d81; font-weight: 600; }}
          .error {{
            background: #fff0f0;
            border: 1px solid #f7b4b4;
            color: #9b1c1c;
            border-radius: 8px;
            padding: 0.7rem 0.8rem;
            margin-bottom: 0.8rem;
          }}
          .dashboard {{ display: grid; gap: 1.2rem; grid-template-columns: 1fr 1fr; align-items: start; }}
          ul {{ margin: 0.4rem 0 0; padding-left: 1.2rem; }}
          @media (max-width: 800px) {{ .dashboard {{ grid-template-columns: 1fr; }} }}
        </style>
      </head>
      <body>
        <div class=\"topbar\">Codex Activity Business Portal</div>
        <main class=\"layout\">{body}</main>
      </body>
    </html>
    """


def options_for_orgs(orgs: list[Organisation], selected: str | None = None) -> str:
    rows = ["<option value=''>-- Select organisation --</option>"]
    for org in orgs:
        chosen = " selected" if selected and str(org.id) == selected else ""
        rows.append(f"<option value='{org.id}'{chosen}>{escape(org.name)}</option>")
    return "".join(rows)


def login_page(orgs: list[Organisation], error: str | None = None, email: str = "", selected_org: str | None = None) -> str:
    error_block = f"<div class='error'>{escape(error)}</div>" if error else ""
    body = f"""
      <section class=\"card\" style=\"max-width:520px;margin:0 auto;\">
        <h1>Sign in</h1>
        <p class=\"subtle\">Access your organisation workspace.</p>
        {error_block}
        <form method=\"post\" action=\"/login\" class=\"form-grid\">
          <label for=\"organisation_id\">Organisation</label>
          <select id=\"organisation_id\" name=\"organisation_id\" required>
            {options_for_orgs(orgs, selected_org)}
          </select>

          <label for=\"email\">Email</label>
          <input id=\"email\" name=\"email\" type=\"email\" required value=\"{escape(email)}\" />

          <label for=\"password\">Password</label>
          <input id=\"password\" name=\"password\" type=\"password\" required />

          <button type=\"submit\">Log in</button>
        </form>
        <a class=\"link\" href=\"/signup\">Create account</a>
      </section>
    """
    return render_shell("Login", body)


def signup_page(orgs: list[Organisation], error: str | None = None, email: str = "") -> str:
    error_block = f"<div class='error'>{escape(error)}</div>" if error else ""
    body = f"""
      <section class=\"card\" style=\"max-width:560px;margin:0 auto;\">
        <h1>Create account</h1>
        <p class=\"subtle\">Join an existing organisation or create a new one.</p>
        {error_block}
        <form method=\"post\" action=\"/signup\" class=\"form-grid\">
          <label for=\"organisation_id\">Organisation</label>
          <select id=\"organisation_id\" name=\"organisation_id\">
            {options_for_orgs(orgs)}
          </select>

          <label for=\"new_organisation\">Or create new organisation</label>
          <input id=\"new_organisation\" name=\"new_organisation\" type=\"text\" placeholder=\"Acme Corporation\" />

          <label for=\"email\">Email</label>
          <input id=\"email\" name=\"email\" type=\"email\" required value=\"{escape(email)}\" />

          <label for=\"password\">Password</label>
          <input id=\"password\" name=\"password\" type=\"password\" required minlength=\"8\" />

          <button type=\"submit\">Create account</button>
        </form>
        <a class=\"link\" href=\"/\">Back to login</a>
      </section>
    """
    return render_shell("Create account", body)


def dashboard_page(user: User, members: list[User]) -> str:
    member_rows = "".join(f"<li>{escape(member.email)}</li>" for member in members)
    body = f"""
      <section class=\"dashboard\">
        <article class=\"card\">
          <h1>Organisation: {escape(user.organisation.name)}</h1>
          <p><strong>Welcome {escape(user.email)}</strong></p>
          <p class=\"subtle\">Signed in to your shared workspace.</p>
          <form method=\"post\" action=\"/logout\">
            <button type=\"submit\">Logout</button>
          </form>
        </article>
        <article class=\"card\">
          <h2>Members</h2>
          <ul>{member_rows}</ul>
        </article>
      </section>
    """
    return render_shell("Dashboard", body)


@app.on_event("startup")
def on_startup() -> None:
    ensure_database()


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> str:
    user_id = request.session.get("user_id")
    with SessionLocal() as db:
        if user_id:
            user = db.get(User, user_id)
            if user:
                members = db.scalars(select(User).where(User.organisation_id == user.organisation_id).order_by(User.email)).all()
                return dashboard_page(user, members)
            request.session.clear()
        orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
    return login_page(orgs)


@app.post("/login")
def login(request: Request, organisation_id: int = Form(...), email: str = Form(...), password: str = Form(...)):
    with SessionLocal() as db:
        user = db.scalar(
            select(User)
            .where(User.email == email.strip().lower())
            .where(User.organisation_id == organisation_id)
        )
        if not user or not pwd_context.verify(password, user.hashed_pw):
            orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
            return HTMLResponse(login_page(orgs, "Invalid credentials for selected organisation.", email, str(organisation_id)), status_code=400)

        request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@app.get("/signup", response_class=HTMLResponse)
def signup_form() -> str:
    with SessionLocal() as db:
        orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
    return signup_page(orgs)


@app.post("/signup")
def signup(
    organisation_id: str = Form(""),
    new_organisation: str = Form(""),
    email: str = Form(...),
    password: str = Form(...),
):
    normal_email = email.strip().lower()
    if len(password) < 8:
        with SessionLocal() as db:
            orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
        return HTMLResponse(signup_page(orgs, "Password must be at least 8 characters.", normal_email), status_code=400)

    with SessionLocal() as db:
        org: Organisation | None = None
        org_name = new_organisation.strip()
        if org_name:
            org = db.scalar(select(Organisation).where(Organisation.name == org_name))
            if not org:
                org = Organisation(name=org_name)
                db.add(org)
                db.flush()
        elif organisation_id:
            org = db.get(Organisation, int(organisation_id))

        if not org:
            orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
            return HTMLResponse(signup_page(orgs, "Select an organisation or create a new one.", normal_email), status_code=400)

        user = User(email=normal_email, hashed_pw=pwd_context.hash(password), organisation_id=org.id)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
            return HTMLResponse(signup_page(orgs, "Email already exists.", normal_email), status_code=400)

    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
