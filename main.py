import os
from typing import Optional

from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import ForeignKey, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://codex_app:codex_app_password@localhost/codex_activity_app",
)
SECRET_KEY = os.getenv("SESSION_SECRET", "dev-only-secret-change-me")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Base(DeclarativeBase):
    pass


class Organisation(Base):
    __tablename__ = "organisation"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    users: Mapped[list["User"]] = relationship(back_populates="organisation")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_pw: Mapped[str] = mapped_column(String(255))
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisation.id"), index=True)

    organisation: Mapped[Organisation] = relationship(back_populates="users")


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


def base_template(content: str, title: str = "Business Portal") -> str:
    return f"""
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>{title}</title>
        <style>
          :root {{
            --brand: #0f4c81;
            --brand-accent: #2a9d8f;
            --text: #1f2937;
            --muted: #6b7280;
            --bg: #f3f6fb;
            --panel: #ffffff;
            --border: #dbe4ee;
          }}

          * {{ box-sizing: border-box; }}

          body {{
            margin: 0;
            min-height: 100vh;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            color: var(--text);
            background: linear-gradient(180deg, #e9f0f8 0%, var(--bg) 100%);
          }}

          .shell {{
            max-width: 980px;
            margin: 2rem auto;
            padding: 0 1rem;
          }}

          .card {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 8px 26px rgba(15, 76, 129, 0.08);
          }}

          h1 {{ margin: 0 0 0.5rem; color: var(--brand); }}
          h2 {{ margin: 0 0 1rem; color: var(--brand); }}
          p {{ color: var(--muted); }}

          form {{ display: grid; gap: 0.8rem; margin-top: 1rem; }}
          label {{ font-weight: 600; font-size: 0.95rem; }}
          input, select {{
            width: 100%;
            border: 1px solid #c7d6e5;
            background: #fff;
            border-radius: 8px;
            padding: 0.65rem;
            font-size: 1rem;
          }}

          .btn {{
            border: 0;
            border-radius: 8px;
            background: var(--brand);
            color: white;
            font-size: 0.95rem;
            font-weight: 600;
            padding: 0.7rem 1rem;
            cursor: pointer;
          }}

          .btn:hover {{ background: #0b3c66; }}
          .btn.secondary {{ background: var(--brand-accent); }}

          .actions {{ display: flex; gap: 0.75rem; align-items: center; margin-top: 1rem; }}
          .alert {{ padding: 0.75rem; border-radius: 8px; background: #fff4e5; color: #92400e; border: 1px solid #f1d5a8; }}
          a {{ color: var(--brand); font-weight: 600; text-decoration: none; }}

          .members {{ margin-top: 1rem; border-top: 1px solid var(--border); padding-top: 1rem; }}
          ul {{ margin: 0.4rem 0 0; padding-left: 1rem; }}
        </style>
      </head>
      <body>
        <div class=\"shell\">{content}</div>
      </body>
    </html>
    """


def render_login(orgs: list[Organisation], error: Optional[str] = None) -> HTMLResponse:
    error_html = f'<div class="alert">{error}</div>' if error else ""
    org_options = "".join([f'<option value="{o.id}">{o.name}</option>' for o in orgs])
    return HTMLResponse(
        base_template(
            f"""
            <div class=\"card\">
              <h1>Business Portal Login</h1>
              <p>Sign in to access your organisation workspace.</p>
              {error_html}
              <form method=\"post\" action=\"/login\">
                <div>
                  <label for=\"organisation_id\">Organisation</label>
                  <select id=\"organisation_id\" name=\"organisation_id\" required>{org_options}</select>
                </div>
                <div>
                  <label for=\"email\">Email</label>
                  <input id=\"email\" type=\"email\" name=\"email\" required />
                </div>
                <div>
                  <label for=\"password\">Password</label>
                  <input id=\"password\" type=\"password\" name=\"password\" required />
                </div>
                <button class=\"btn\" type=\"submit\">Log in</button>
              </form>
              <div class=\"actions\">
                <span>Need an account?</span>
                <a href=\"/register\">Create account</a>
              </div>
            </div>
            """
        )
    )


def render_register(orgs: list[Organisation], error: Optional[str] = None) -> HTMLResponse:
    error_html = f'<div class="alert">{error}</div>' if error else ""
    org_options = "".join([f'<option value="{o.id}">{o.name}</option>' for o in orgs])
    return HTMLResponse(
        base_template(
            f"""
            <div class=\"card\">
              <h1>Create Account</h1>
              <p>Create your user and select an existing organisation or define a new one.</p>
              {error_html}
              <form method=\"post\" action=\"/register\">
                <div>
                  <label for=\"organisation_id\">Existing Organisation</label>
                  <select id=\"organisation_id\" name=\"organisation_id\">
                    <option value=\"\">-- Select existing --</option>
                    {org_options}
                  </select>
                </div>
                <div>
                  <label for=\"new_organisation\">Or create new organisation</label>
                  <input id=\"new_organisation\" type=\"text\" name=\"new_organisation\" placeholder=\"e.g. Northwind Finance\" />
                </div>
                <div>
                  <label for=\"email\">Email</label>
                  <input id=\"email\" type=\"email\" name=\"email\" required />
                </div>
                <div>
                  <label for=\"password\">Password</label>
                  <input id=\"password\" type=\"password\" name=\"password\" required />
                </div>
                <button class=\"btn secondary\" type=\"submit\">Create account</button>
              </form>
              <div class=\"actions\">
                <a href=\"/\">Back to login</a>
              </div>
            </div>
            """
        )
    )


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    user_id = request.session.get("user_id")
    if not user_id:
        with SessionLocal() as db:
            orgs = list(db.scalars(select(Organisation).order_by(Organisation.name)))
            return render_login(orgs)

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            request.session.clear()
            return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

        org = user.organisation
        members = list(db.scalars(select(User).where(User.organisation_id == org.id).order_by(User.email)))

    member_rows = "".join([f"<li>{m.email}</li>" for m in members])
    return HTMLResponse(
        base_template(
            f"""
            <div class=\"card\">
              <h1>Organisation: {org.name}</h1>
              <h2>Welcome {user.email}</h2>
              <div class=\"members\">
                <strong>Members</strong>
                <ul>{member_rows}</ul>
              </div>
              <form method=\"post\" action=\"/logout\" class=\"actions\">
                <button type=\"submit\" class=\"btn\">Logout</button>
              </form>
            </div>
            """
        )
    )


@app.get("/register", response_class=HTMLResponse)
def register_page() -> HTMLResponse:
    with SessionLocal() as db:
        orgs = list(db.scalars(select(Organisation).order_by(Organisation.name)))
    return render_register(orgs)


@app.post("/register", response_class=HTMLResponse)
def register(
    email: str = Form(...),
    password: str = Form(...),
    organisation_id: Optional[str] = Form(None),
    new_organisation: Optional[str] = Form(None),
) -> HTMLResponse:
    clean_new_org = (new_organisation or "").strip()

    with SessionLocal() as db:
        existing_user = db.scalar(select(User).where(User.email == email.lower()))
        if existing_user:
            orgs = list(db.scalars(select(Organisation).order_by(Organisation.name)))
            return render_register(orgs, "Email is already in use.")

        org: Optional[Organisation] = None
        if clean_new_org:
            org = db.scalar(select(Organisation).where(Organisation.name == clean_new_org))
            if not org:
                org = Organisation(name=clean_new_org)
                db.add(org)
                db.flush()
        elif organisation_id:
            org = db.get(Organisation, int(organisation_id))

        if not org:
            orgs = list(db.scalars(select(Organisation).order_by(Organisation.name)))
            return render_register(orgs, "Please select an organisation or create a new one.")

        user = User(
            email=email.lower(),
            hashed_pw=pwd_context.hash(password),
            organisation_id=org.id,
        )
        db.add(user)
        db.commit()

    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    organisation_id: int = Form(...),
) -> HTMLResponse:
    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                User.email == email.lower(),
                User.organisation_id == organisation_id,
            )
        )
        if not user or not pwd_context.verify(password, user.hashed_pw):
            orgs = list(db.scalars(select(Organisation).order_by(Organisation.name)))
            return render_login(orgs, "Invalid credentials or organisation selection.")

        request.session["user_id"] = user.id

    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
