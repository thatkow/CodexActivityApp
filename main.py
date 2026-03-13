import base64
import hashlib
import hmac
import html
import os
import secrets
from datetime import datetime, timezone
from typing import Generator
from urllib.parse import quote

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, create_engine, select
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


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    submitted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    marker_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    marker_file_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    project_coordinator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_coordinator_email: Mapped[str] = mapped_column(String(255), nullable=False)
    marker_design_contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    marker_design_contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    product_contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    tg_contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tg_contact_email: Mapped[str] = mapped_column(String(255), nullable=False)

    organisation: Mapped[Organisation] = relationship()
    submitted_by: Mapped[User] = relationship()


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://codex_app:codex_app_password@127.0.0.1:3306/codex_activity_app",
)
SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-this-in-production")
PANEL_ADMIN = os.getenv("PANEL_ADMIN", "admin")
PANEL_ADMIN_PW = os.getenv("PANEL_ADMIN_PW", "password")

REQUIRED_MARKER_COLUMNS = {
    "MarkerName",
    "TargetSequence",
    "ReferenceGenome",
    "Chrom",
    "ChromPosPhysical",
    "ChromPosGenetic",
    "VariantAllelesDef",
    "MarkerType",
    "EssentialMarker",
    "MinorAlleleFrequency",
    "Quality",
    "Comments",
}

PENDING_UPLOADS: dict[str, dict[str, str | bytes | int]] = {}

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


def sign_session_value(raw_value: str) -> str:
    raw = raw_value.encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return f"{raw_value}.{sig}"


def parse_session_value(cookie_value: str | None) -> str | None:
    if not cookie_value or "." not in cookie_value:
        return None
    raw_value, sig = cookie_value.split(".", 1)
    expected = hmac.new(SECRET_KEY.encode("utf-8"), raw_value.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return raw_value


def parse_user_id(request: Request) -> int | None:
    raw = parse_session_value(request.cookies.get("session"))
    if not raw or not raw.isdigit():
        return None
    return int(raw)


def is_admin_logged_in(request: Request) -> bool:
    return parse_session_value(request.cookies.get("admin_session")) == PANEL_ADMIN


def marker_template_file() -> str:
    return (
        "MarkerName\tTargetSequence\tReferenceGenome\tChrom\tChromPosPhysical\tChromPosGenetic\tVariantAllelesDef\tMarkerType\tEssentialMarker\tMinorAlleleFrequency\tQuality\tComments\n"
        "Chr01_20858452\tGTTCTTTGGGTACTGTAGATCCAATCCATCACTGTTTTAAAAGGAGAATATTTCATTCATTGATGATATGCAGGAAGATGTGTTGGAAAGAGCCAAAAAAGCTAAGGAGAAAGCAGCACGGGAGGCCATGGAGGCACAAGGACTAATTCC[A/G]AAGTCTACTGTAGTAGATACACCAGCAACTGATAGTGTTGATTCTGTTACTGCATCATCAACGGTCAGTGAGATTAGTGCTGCAGATGCATCCTCATTGTCTAGTCCGACTACTCCCATGTCCCAGTCATATAGAGGTCCTGCTGATAAG\tCastanea dentata v1.1\tChr01\t20858452\t72.74810491\t[A/G]\tSNP\tNO\t0.350817236\t7\t\n"
        "Chr01_21504745\tAGATTTTCACTTCCCGCAGCAGATAAGCCTTAGACAACGGTATGTTTATCCATACTATATGCACATCATAGATTTCTTTTCTATTTTTTTAGGTGGTGGAAAAATGGAATTAGCTATTATTTCACTTCTGGAACTGCATCTGCTGTCTAC[G/A]AAATCAGCTACTACCTCTAAACAGATTAATTATAGAAGATTGCGTTGAGTTAAATAGGTAATGATTTAGATTGTCTTAAGTTAATATGTAATGATTCAGTTTCTTTTGCTGCAGGTATGCATTGTTGGGTAACAGTTTAAGTATAGCAGT\tCastanea dentata v1.1\tChr01\t21504745\t73.21579093\t[G/A]\tSNP\tNO\t0.453194651\t7\t\n"
    )


def parse_columns(file_bytes: bytes) -> tuple[set[str], str]:
    first_line = file_bytes.decode("utf-8", errors="ignore").splitlines()[0] if file_bytes else ""
    delimiter = "\t" if "\t" in first_line else ","
    cols = {c.strip() for c in first_line.split(delimiter) if c.strip()}
    return cols, delimiter


def page_template(title: str, body: str) -> str:
    return f"""
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>{title}</title>
        <style>
          body {{ margin: 0; font-family: Inter, Segoe UI, Roboto, Arial, sans-serif; background: #eef2f7; color: #12263a; }}
          .shell {{ min-height: 100vh; display: grid; place-items: center; padding: 24px; }}
          .card {{ width: min(980px, 100%); background: #fff; border-radius: 14px; box-shadow: 0 10px 30px rgba(16, 42, 67, 0.12); overflow: hidden; }}
          .header {{ background: linear-gradient(100deg, #1f3c88, #2d6cdf); color: white; padding: 22px 28px; font-size: 1.25rem; font-weight: 700; }}
          .content {{ padding: 26px 28px 30px; }}
          h1, h2, h3, p {{ margin-top: 0; }}
          label {{ font-size: 0.93rem; font-weight: 600; display: block; margin: 14px 0 6px; }}
          input, select, button {{ width: 100%; padding: 10px 12px; border: 1px solid #c4cfdb; border-radius: 9px; font-size: 0.95rem; box-sizing: border-box; }}
          button {{ margin-top: 16px; background: #1f3c88; color: #fff; border: none; font-weight: 700; cursor: pointer; }}
          .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start; }}
          .muted {{ color: #5f6c7b; }}
          .error {{ background: #ffe1e1; color: #8a1717; border-radius: 8px; padding: 10px; margin-bottom: 12px; }}
          .success {{ background: #e5ffe9; color: #1d662b; border-radius: 8px; padding: 10px; margin-bottom: 12px; }}
          .link {{ margin-top: 14px; display: inline-block; color: #1f3c88; text-decoration: none; font-weight: 600; }}
          ul {{ margin: 0; padding-left: 20px; }}
          .top-actions {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 14px; }}
          .logout, .action {{ max-width: 250px; margin: 0; background: #305ca8; text-decoration: none; display: inline-flex; justify-content: center; align-items: center; color: #fff; font-weight: 700; }}
          table {{ width: 100%; border-collapse: collapse; }}
          td, th {{ border-bottom: 1px solid #e0e7f1; padding: 10px 8px; text-align: left; }}
          tr.clickable-row {{ cursor: pointer; }}
          .contact-grid {{ display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 12px; align-items: center; margin-bottom: 10px; }}
          .contact-grid label {{ margin: 0; }}
          @media (max-width: 768px) {{ .row, .contact-grid {{ grid-template-columns: 1fr; }} }}
        </style>
      </head>
      <body>
        <div class=\"shell\"><div class=\"card\">{body}</div></div>
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
            <select id=\"organisation_id\" name=\"organisation_id\" required>{org_options}</select>
            <label for=\"email\">Email</label><input id=\"email\" name=\"email\" type=\"email\" required />
            <label for=\"password\">Password</label><input id=\"password\" name=\"password\" type=\"password\" required />
            <button type=\"submit\">Login</button>
          </form>
          <a class=\"link\" href=\"/register\">Create account</a>
          <a class=\"link\" href=\"/admin\" style=\"margin-left:16px\">Admin</a>
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
            <label for=\"email\">Email</label><input id=\"email\" name=\"email\" type=\"email\" required />
            <label for=\"password\">Password</label><input id=\"password\" name=\"password\" type=\"password\" minlength=\"8\" required />
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


def submission_upload_form(error: str = "") -> str:
    error_html = f'<div class="error">{error}</div>' if error else ""
    return page_template(
        "Submit Marker Panel",
        f"""
        <div class=\"header\">Submit Marker Panel</div>
        <div class=\"content\">
          {error_html}
          <p>Upload a marker panel file. You can download an example format <a href=\"/submit-marker-panel/template\">here</a>.</p>
          <form method=\"post\" action=\"/submit-marker-panel/upload\" enctype=\"multipart/form-data\">
            <label for=\"marker_file\">Marker Panel File</label>
            <input id=\"marker_file\" type=\"file\" name=\"marker_file\" required />
            <button type=\"submit\">Validate File</button>
          </form>
          <a class=\"link\" href=\"/\">Back to dashboard</a>
        </div>
        """,
    )


def submission_contacts_form(token: str, filename: str) -> str:
    return page_template(
        "Submission Contacts",
        f"""
        <div class=\"header\">Submission Contacts</div>
        <div class=\"content\">
          <p class=\"muted\">Validated file: <strong>{html.escape(filename)}</strong></p>
          <form method=\"post\" action=\"/submit-marker-panel/contacts\">
            <input type=\"hidden\" name=\"token\" value=\"{html.escape(token)}\" />
            <div class=\"contact-grid\"><label>Project Coordinator(s)</label><input name=\"project_coordinator_name\" placeholder=\"Name\" required /><input name=\"project_coordinator_email\" type=\"email\" placeholder=\"Email\" required /></div>
            <div class=\"contact-grid\"><label>Marker Design Contact(s)</label><input name=\"marker_design_contact_name\" placeholder=\"Name\" required /><input name=\"marker_design_contact_email\" type=\"email\" placeholder=\"Email\" required /></div>
            <div class=\"contact-grid\"><label>Contact(s) for receiving product name and custom code</label><input name=\"product_contact_name\" placeholder=\"Name\" required /><input name=\"product_contact_email\" type=\"email\" placeholder=\"Email\" required /></div>
            <div class=\"contact-grid\"><label>Contact(s) for the TG</label><input name=\"tg_contact_name\" placeholder=\"Name\" required /><input name=\"tg_contact_email\" type=\"email\" placeholder=\"Email\" required /></div>
            <button type=\"submit\">Submit Marker Panel</button>
          </form>
        </div>
        """,
    )


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    with SessionLocal() as db:
        user_id = parse_user_id(request)
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

        members = db.scalars(select(User).where(User.organisation_id == user.organisation_id).order_by(User.email)).all()
        member_items = "".join(f"<li>{html.escape(member.email)}</li>" for member in members)
        success = "<div class=\"success\">Submission Successful! We'll get back to you in a few days.</div>" if request.query_params.get("submission_success") == "1" else ""
        return HTMLResponse(
            page_template(
                "Dashboard",
                f"""
                <div class=\"header\">Organisation: {html.escape(user.organisation.name)} </div>
                <div class=\"content\">
                  {success}
                  <div class=\"top-actions\">
                    <div><h2>Welcome {html.escape(user.email)}</h2><p class=\"muted\">Logged into your organisation workspace.</p></div>
                    <form method=\"post\" action=\"/logout\" style=\"margin:0\"><button type=\"submit\" class=\"logout\">Logout</button></form>
                  </div>
                  <div style=\"margin-bottom: 14px\"><a class=\"action\" href=\"/submit-marker-panel\">Submit Marker Panel</a></div>
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
        user = db.scalar(select(User).where(User.email == email.strip().lower(), User.organisation_id == organisation_id))
        if not user or not verify_password(password, user.hashed_pw):
            return HTMLResponse(login_form(options, "Invalid credentials or organisation selection."), status_code=400)

        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie("session", sign_session_value(str(user.id)), httponly=True, samesite="lax")
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
        response.set_cookie("session", sign_session_value(str(user.id)), httponly=True, samesite="lax")
        return response


@app.get("/submit-marker-panel", response_class=HTMLResponse, response_model=None)
def submit_marker_panel_page(request: Request) -> HTMLResponse | RedirectResponse:
    if parse_user_id(request) is None:
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(submission_upload_form())


@app.get("/submit-marker-panel/template")
def submit_marker_panel_template() -> Response:
    return Response(
        content=marker_template_file(),
        media_type="text/tab-separated-values",
        headers={"Content-Disposition": 'attachment; filename="marker-panel-template.tsv"'},
    )


@app.post("/submit-marker-panel/upload", response_model=None)
async def submit_marker_panel_upload(request: Request, marker_file: UploadFile = File(...)) -> HTMLResponse | RedirectResponse:
    user_id = parse_user_id(request)
    if user_id is None:
        return RedirectResponse(url="/", status_code=303)

    file_bytes = await marker_file.read()
    if not file_bytes:
        return HTMLResponse(submission_upload_form("File is empty."), status_code=400)

    cols, _ = parse_columns(file_bytes)
    missing = sorted(REQUIRED_MARKER_COLUMNS - cols)
    if missing:
        return HTMLResponse(
            page_template(
                "Marker Panel Validation",
                f"""
                <div class=\"header\">Marker Panel Validation Failed</div>
                <div class=\"content\">
                  <div class=\"error\">Missing required columns: {", ".join(html.escape(c) for c in missing)}</div>
                  <p>Columns can be in any order, but all required columns must exist.</p>
                  <a class=\"link\" href=\"/submit-marker-panel\">Try again</a>
                </div>
                """,
            ),
            status_code=400,
        )

    token = secrets.token_urlsafe(24)
    PENDING_UPLOADS[token] = {
        "user_id": user_id,
        "filename": marker_file.filename or "marker-panel.tsv",
        "file_bytes": file_bytes,
    }
    return RedirectResponse(url=f"/submit-marker-panel/contacts?token={quote(token)}", status_code=303)


@app.get("/submit-marker-panel/contacts", response_class=HTMLResponse, response_model=None)
def submit_marker_panel_contacts(request: Request, token: str) -> HTMLResponse | RedirectResponse:
    user_id = parse_user_id(request)
    pending = PENDING_UPLOADS.get(token)
    if user_id is None or not pending or pending.get("user_id") != user_id:
        return RedirectResponse(url="/submit-marker-panel", status_code=303)
    return HTMLResponse(submission_contacts_form(token, str(pending["filename"])))


@app.post("/submit-marker-panel/contacts", response_model=None)
def submit_marker_panel_finalize(
    request: Request,
    token: str = Form(...),
    project_coordinator_name: str = Form(...),
    project_coordinator_email: str = Form(...),
    marker_design_contact_name: str = Form(...),
    marker_design_contact_email: str = Form(...),
    product_contact_name: str = Form(...),
    product_contact_email: str = Form(...),
    tg_contact_name: str = Form(...),
    tg_contact_email: str = Form(...),
) -> RedirectResponse:
    user_id = parse_user_id(request)
    pending = PENDING_UPLOADS.get(token)
    if user_id is None or not pending or pending.get("user_id") != user_id:
        return RedirectResponse(url="/submit-marker-panel", status_code=303)

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            return RedirectResponse(url="/", status_code=303)

        submission = Submission(
            organisation_id=user.organisation_id,
            submitted_by_user_id=user.id,
            marker_filename=str(pending["filename"]),
            marker_file_blob=bytes(pending["file_bytes"]),
            submitted_at=datetime.now(timezone.utc),
            project_coordinator_name=project_coordinator_name.strip(),
            project_coordinator_email=project_coordinator_email.strip(),
            marker_design_contact_name=marker_design_contact_name.strip(),
            marker_design_contact_email=marker_design_contact_email.strip(),
            product_contact_name=product_contact_name.strip(),
            product_contact_email=product_contact_email.strip(),
            tg_contact_name=tg_contact_name.strip(),
            tg_contact_email=tg_contact_email.strip(),
        )
        db.add(submission)
        db.commit()

    PENDING_UPLOADS.pop(token, None)
    return RedirectResponse(url="/?submission_success=1", status_code=303)


@app.get("/admin", response_class=HTMLResponse, response_model=None)
def admin_login_page(request: Request) -> HTMLResponse | RedirectResponse:
    if is_admin_logged_in(request):
        return RedirectResponse(url="/admin/submissions", status_code=303)
    return HTMLResponse(
        page_template(
            "Admin Login",
            """
            <div class=\"header\">Marker Panel Admin</div>
            <div class=\"content\">
              <form method=\"post\" action=\"/admin/login\">
                <label>Username</label><input name=\"username\" required />
                <label>Password</label><input name=\"password\" type=\"password\" required />
                <button type=\"submit\">Login</button>
              </form>
              <a class=\"link\" href=\"/\">Back to app</a>
            </div>
            """,
        )
    )


@app.post("/admin/login", response_model=None)
def admin_login(username: str = Form(...), password: str = Form(...)) -> HTMLResponse | RedirectResponse:
    if username != PANEL_ADMIN or password != PANEL_ADMIN_PW:
        return HTMLResponse(
            page_template(
                "Admin Login",
                """
                <div class=\"header\">Marker Panel Admin</div>
                <div class=\"content\"><div class=\"error\">Invalid admin credentials.</div><a class=\"link\" href=\"/admin\">Try again</a></div>
                """,
            ),
            status_code=401,
        )

    response = RedirectResponse(url="/admin/submissions", status_code=303)
    response.set_cookie("admin_session", sign_session_value(PANEL_ADMIN), httponly=True, samesite="lax")
    return response


@app.get("/admin/submissions", response_class=HTMLResponse, response_model=None)
def admin_submissions(request: Request) -> HTMLResponse | RedirectResponse:
    if not is_admin_logged_in(request):
        return RedirectResponse(url="/admin", status_code=303)

    with SessionLocal() as db:
        submissions = db.scalars(select(Submission).order_by(Submission.submitted_at.desc())).all()

    rows = "".join(
        f"<tr class='clickable-row' onclick=\"window.location='/admin/submissions/{s.id}'\"><td>{s.id}</td><td>{html.escape(s.marker_filename)}</td><td>{html.escape(s.project_coordinator_name)}</td><td>{s.submitted_at}</td></tr>"
        for s in submissions
    )
    if not rows:
        rows = "<tr><td colspan='4'>No submissions yet.</td></tr>"

    return HTMLResponse(
        page_template(
            "Admin Submissions",
            f"""
            <div class=\"header\">Submissions</div>
            <div class=\"content\">
              <table><thead><tr><th>ID</th><th>File</th><th>Project Coordinator</th><th>Submitted At</th></tr></thead><tbody>{rows}</tbody></table>
            </div>
            """,
        )
    )


@app.get("/admin/submissions/{submission_id}", response_class=HTMLResponse, response_model=None)
def admin_submission_detail(request: Request, submission_id: int) -> HTMLResponse | RedirectResponse:
    if not is_admin_logged_in(request):
        return RedirectResponse(url="/admin", status_code=303)

    with SessionLocal() as db:
        submission = db.get(Submission, submission_id)
        if not submission:
            return RedirectResponse(url="/admin/submissions", status_code=303)

        return HTMLResponse(
            page_template(
                f"Submission {submission.id}",
                f"""
                <div class=\"header\">Submission #{submission.id}</div>
                <div class=\"content\">
                  <p><strong>File:</strong> {html.escape(submission.marker_filename)}</p>
                  <p><a class=\"link\" href=\"/admin/submissions/{submission.id}/file\">Download marker file</a></p>
                  <div class=\"contact-grid\"><label>Project Coordinator(s)</label><input value=\"{html.escape(submission.project_coordinator_name)}\" readonly /><input value=\"{html.escape(submission.project_coordinator_email)}\" readonly /></div>
                  <div class=\"contact-grid\"><label>Marker Design Contact(s)</label><input value=\"{html.escape(submission.marker_design_contact_name)}\" readonly /><input value=\"{html.escape(submission.marker_design_contact_email)}\" readonly /></div>
                  <div class=\"contact-grid\"><label>Contact(s) for receiving product name and custom code</label><input value=\"{html.escape(submission.product_contact_name)}\" readonly /><input value=\"{html.escape(submission.product_contact_email)}\" readonly /></div>
                  <div class=\"contact-grid\"><label>Contact(s) for the TG</label><input value=\"{html.escape(submission.tg_contact_name)}\" readonly /><input value=\"{html.escape(submission.tg_contact_email)}\" readonly /></div>
                  <a class=\"link\" href=\"/admin/submissions\">Back to submissions</a>
                </div>
                """,
            )
        )


@app.get("/admin/submissions/{submission_id}/file", response_model=None)
def admin_submission_file(request: Request, submission_id: int) -> Response | RedirectResponse:
    if not is_admin_logged_in(request):
        return RedirectResponse(url="/admin", status_code=303)

    with SessionLocal() as db:
        submission = db.get(Submission, submission_id)
        if not submission:
            return RedirectResponse(url="/admin/submissions", status_code=303)
        return Response(
            content=submission.marker_file_blob,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{submission.marker_filename}"'},
        )


@app.post("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session")
    return response
