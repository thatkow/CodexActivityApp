import base64
import hashlib
import hmac
import html
import os
from typing import Any

import pymysql
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware


app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-me-in-production"),
    same_site="lax",
    https_only=False,
)


PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 390000


def db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "codex_app"),
        "password": os.getenv("MYSQL_PASSWORD", "codex_app_password"),
        "database": os.getenv("MYSQL_DATABASE", "codex_activity_app"),
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }


def get_connection() -> pymysql.connections.Connection:
    return pymysql.connect(**db_config())


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return (
        f"pbkdf2_{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(digest).decode('ascii')}"
    )


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        _, iterations, salt_b64, digest_b64 = hashed_password.split("$")
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
        computed = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(expected, computed)
    except (ValueError, TypeError):
        return False


def init_db() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS organisations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE
                ) ENGINE=InnoDB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    hashed_pw VARCHAR(255) NOT NULL,
                    organisation_id INT NOT NULL,
                    CONSTRAINT fk_users_organisation
                        FOREIGN KEY (organisation_id) REFERENCES organisations(id)
                        ON DELETE RESTRICT ON UPDATE CASCADE
                ) ENGINE=InnoDB;
                """
            )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def fetch_organisations() -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM organisations ORDER BY name")
            return list(cur.fetchall())


def render_page(body: str, title: str = "Codex Business App") -> str:
    return f"""
    <!doctype html>
    <html lang=\"en\">
    <head>
      <meta charset=\"UTF-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
      <title>{html.escape(title)}</title>
      <style>
        :root {{
          --bg: #f1f5f9;
          --card: #ffffff;
          --text: #111827;
          --muted: #6b7280;
          --brand: #1d4ed8;
          --brand-dark: #1e3a8a;
          --border: #d1d5db;
          --danger: #b91c1c;
          font-family: Inter, Segoe UI, Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: var(--bg); color: var(--text); }}
        .topbar {{
          background: linear-gradient(90deg, var(--brand-dark), var(--brand));
          color: white;
          padding: 1rem 2rem;
          font-weight: 600;
          letter-spacing: 0.02em;
          box-shadow: 0 4px 16px rgba(0,0,0,0.18);
        }}
        .wrap {{ max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }}
        .card {{
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 12px;
          box-shadow: 0 10px 25px rgba(2, 6, 23, 0.08);
          padding: 1.5rem;
        }}
        h1, h2 {{ margin-top: 0; }}
        label {{ display: block; margin: 0.7rem 0 0.3rem; font-weight: 600; }}
        input, select {{
          width: 100%;
          padding: 0.7rem 0.75rem;
          border-radius: 8px;
          border: 1px solid var(--border);
          font-size: 0.95rem;
        }}
        button {{
          background: var(--brand);
          color: white;
          border: none;
          border-radius: 8px;
          padding: 0.7rem 1rem;
          margin-top: 1rem;
          cursor: pointer;
          font-weight: 700;
        }}
        button:hover {{ background: var(--brand-dark); }}
        .error {{ background: #fee2e2; color: var(--danger); padding: 0.7rem; border-radius: 8px; margin-bottom: 0.8rem; }}
        .grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; }}
        .muted {{ color: var(--muted); }}
        .members-list {{ margin: 0; padding-left: 1.2rem; line-height: 1.7; }}
        .logout {{ float: right; background: #334155; }}
        a {{ color: var(--brand); font-weight: 600; text-decoration: none; }}
      </style>
    </head>
    <body>
      <div class=\"topbar\">Codex Activity Business Portal</div>
      <div class=\"wrap\">{body}</div>
    </body>
    </html>
    """


def login_form(error: str = "") -> str:
    organisations = fetch_organisations()
    options = "".join(
        f'<option value="{org["id"]}">{html.escape(org["name"])}</option>' for org in organisations
    )
    msg = f'<div class="error">{html.escape(error)}</div>' if error else ""
    return render_page(
        f"""
        <div class=\"card\" style=\"max-width: 500px; margin: 0 auto;\">
          <h2>Sign in</h2>
          <p class=\"muted\">Use your organisation account credentials.</p>
          {msg}
          <form method=\"post\" action=\"/login\">
            <label for=\"organisation_id\">Organisation</label>
            <select id=\"organisation_id\" name=\"organisation_id\" required>
              <option value=\"\">Select organisation...</option>
              {options}
            </select>
            <label for=\"email\">Email</label>
            <input id=\"email\" type=\"email\" name=\"email\" required />
            <label for=\"password\">Password</label>
            <input id=\"password\" type=\"password\" name=\"password\" required />
            <button type=\"submit\">Login</button>
          </form>
          <p class=\"muted\">Need access? <a href=\"/register\">Create account</a></p>
        </div>
        """,
        title="Login",
    )


def register_form(error: str = "") -> str:
    organisations = fetch_organisations()
    options = "".join(
        f'<option value="{org["id"]}">{html.escape(org["name"])}</option>' for org in organisations
    )
    msg = f'<div class="error">{html.escape(error)}</div>' if error else ""
    return render_page(
        f"""
        <div class=\"card\" style=\"max-width: 520px; margin: 0 auto;\">
          <h2>Create account</h2>
          {msg}
          <form method=\"post\" action=\"/register\">
            <label for=\"organisation_id\">Organisation</label>
            <select id=\"organisation_id\" name=\"organisation_id\" required>
              <option value=\"\">Select organisation...</option>
              {options}
              <option value=\"__new__\">+ Create new organisation</option>
            </select>
            <label for=\"new_organisation\">New organisation name (if creating)</label>
            <input id=\"new_organisation\" name=\"new_organisation\" maxlength=\"255\" />
            <label for=\"email\">Email</label>
            <input id=\"email\" type=\"email\" name=\"email\" required />
            <label for=\"password\">Password</label>
            <input id=\"password\" type=\"password\" name=\"password\" required minlength=\"8\" />
            <button type=\"submit\">Create account</button>
          </form>
          <p class=\"muted\"><a href=\"/\">Back to login</a></p>
        </div>
        """,
        title="Create account",
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    user_id = request.session.get("user_id")
    if not user_id:
        return HTMLResponse(login_form())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.email, o.name AS organisation_name
                FROM users u
                JOIN organisations o ON o.id = u.organisation_id
                WHERE u.id = %s
                """,
                (user_id,),
            )
            user = cur.fetchone()
            if not user:
                request.session.clear()
                return HTMLResponse(login_form("Session expired. Please log in again."))

            cur.execute(
                """
                SELECT email
                FROM users
                WHERE organisation_id = (
                    SELECT organisation_id FROM users WHERE id = %s
                )
                ORDER BY email
                """,
                (user_id,),
            )
            members = cur.fetchall()

    members_html = "".join(f"<li>{html.escape(member['email'])}</li>" for member in members)
    body = f"""
      <div class=\"grid\">
        <div class=\"card\">
          <form action=\"/logout\" method=\"post\"><button class=\"logout\" type=\"submit\">Logout</button></form>
          <h1>Organisation: {html.escape(user['organisation_name'])}</h1>
          <h3>Welcome {html.escape(user['email'])}</h3>
          <p class=\"muted\">You are signed in to your organisation workspace.</p>
        </div>
        <div class=\"card\">
          <h2>Members</h2>
          <ul class=\"members-list\">{members_html}</ul>
        </div>
      </div>
    """
    return HTMLResponse(render_page(body, title="Dashboard"))


@app.post("/login")
def login(
    request: Request,
    organisation_id: int = Form(...),
    email: str = Form(...),
    password: str = Form(...),
) -> HTMLResponse | RedirectResponse:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, hashed_pw
                FROM users
                WHERE email = %s AND organisation_id = %s
                """,
                (email.strip().lower(), organisation_id),
            )
            user = cur.fetchone()

    if not user or not verify_password(password, user["hashed_pw"]):
        return HTMLResponse(login_form("Invalid credentials or organisation selection."), status_code=401)

    request.session["user_id"] = user["id"]
    return RedirectResponse(url="/", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_page() -> HTMLResponse:
    return HTMLResponse(register_form())


@app.post("/register")
def register(
    organisation_id: str = Form(...),
    new_organisation: str = Form(""),
    email: str = Form(...),
    password: str = Form(...),
) -> HTMLResponse | RedirectResponse:
    clean_email = email.strip().lower()
    clean_new_org = new_organisation.strip()

    if organisation_id == "__new__" and not clean_new_org:
        return HTMLResponse(register_form("Enter a name for the new organisation."), status_code=400)

    if len(password) < 8:
        return HTMLResponse(register_form("Password must be at least 8 characters."), status_code=400)

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                if organisation_id == "__new__":
                    cur.execute("INSERT INTO organisations (name) VALUES (%s)", (clean_new_org,))
                    selected_org_id = cur.lastrowid
                else:
                    selected_org_id = int(organisation_id)

                cur.execute(
                    "INSERT INTO users (email, hashed_pw, organisation_id) VALUES (%s, %s, %s)",
                    (clean_email, hash_password(password), selected_org_id),
                )
            except pymysql.err.IntegrityError as err:
                if err.args[0] == 1062:
                    return HTMLResponse(
                        register_form("Email or organisation already exists. Try different values."),
                        status_code=409,
                    )
                return HTMLResponse(register_form("Could not create account."), status_code=400)

    return RedirectResponse(url="/", status_code=303)


@app.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
