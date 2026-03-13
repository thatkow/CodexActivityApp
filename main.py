import base64
import csv
import hashlib
import hmac
import io
import os
import secrets
import shutil
import subprocess
import threading
from datetime import datetime
from typing import Generator
from pathlib import Path
from urllib.parse import quote
import html

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, create_engine, select
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
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    date_submitted: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    project_coordinator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_coordinator_email: Mapped[str] = mapped_column(String(255), nullable=False)
    marker_design_contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    marker_design_contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    product_contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    tg_contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tg_contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    checker_container_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checker_exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as dotfile:
        for raw_line in dotfile:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            os.environ.setdefault(key, value)


load_dotenv()

from emails import send_submission_notification

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://codex_app:codex_app_password@127.0.0.1:3306/codex_activity_app",
)
SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-this-in-production")
PANEL_ADMIN = os.getenv("PANEL_ADMIN", "admin")
PANEL_ADMIN_PW = os.getenv("PANEL_ADMIN_PW", "password")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
SUBMISSION_WORKING_DIR = os.getenv("SUBMISSION_WORKING_DIR", "submission_checking_runs")
SUBMISSION_CHECKER_IMAGE = os.getenv("SUBMISSION_CHECKER_IMAGE", "diversityarraystechnology/submission_checking")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

app = FastAPI(title="Codex Activity App")

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

EXAMPLE_MARKER_FILE = """MarkerName,TargetSequence,ReferenceGenome,Chrom,ChromPosPhysical,ChromPosGenetic,VariantAllelesDef,MarkerType,EssentialMarker,MinorAlleleFrequency,Quality,Comments
Chr01_20858452,GTTCTTTGGGTACTGTAGATCCAATCCATCACTGTTTTAAAAGGAGAATATTTCATTCATTGATGATATGCAGGAAGATGTGTTGGAAAGAGCCAAAAAAGCTAAGGAGAAAGCAGCACGGGAGGCCATGGAGGCACAAGGACTAATTCC[A/G]AAGTCTACTGTAGTAGATACACCAGCAACTGATAGTGTTGATTCTGTTACTGCATCATCAACGGTCAGTGAGATTAGTGCTGCAGATGCATCCTCATTGTCTAGTCCGACTACTCCCATGTCCCAGTCATATAGAGGTCCTGCTGATAAG,Castanea dentata v1.1,Chr01,20858452,72.74810491,[A/G],SNP,NO,0.350817236,7,
Chr01_21504745,AGATTTTCACTTCCCGCAGCAGATAAGCCTTAGACAACGGTATGTTTATCCATACTATATGCACATCATAGATTTCTTTTCTATTTTTTTAGGTGGTGGAAAAATGGAATTAGCTATTATTTCACTTCTGGAACTGCATCTGCTGTCTAC[G/A]AAATCAGCTACTACCTCTAAACAGATTAATTATAGAAGATTGCGTTGAGTTAAATAGGTAATGATTTAGATTGTCTTAAGTTAATATGTAATGATTCAGTTTCTTTTGCTGCAGGTATGCATTGTTGGGTAACAGTTTAAGTATAGCAGT,Castanea dentata v1.1,Chr01,21504745,73.21579093,[G/A],SNP,NO,0.453194651,7,
"""


def submission_output_dir(submission_id: int) -> Path:
    return Path(SUBMISSION_WORKING_DIR) / str(submission_id) / "submission_checking_output"


def submission_marker_file_path(submission_id: int) -> Path:
    return Path(SUBMISSION_WORKING_DIR) / str(submission_id) / "submission.csv"


def submission_log_path(submission_id: int) -> Path:
    return submission_output_dir(submission_id) / "docker.log"


def list_submission_output_files(submission_id: int) -> list[str]:
    out_dir = submission_output_dir(submission_id)
    if not out_dir.exists():
        return []
    files: list[str] = []
    for root, _, names in os.walk(out_dir):
        for name in names:
            full_path = Path(root) / name
            rel = full_path.relative_to(out_dir).as_posix()
            files.append(rel)
    return sorted(files)


def run_submission_checker_in_background(submission_id: int) -> None:
    marker_file = submission_marker_file_path(submission_id)
    output_dir = submission_output_dir(submission_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = submission_log_path(submission_id)

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-d",
        "-u",
        f"{os.getuid()}:{os.getgid()}",
        "-v",
        f"{marker_file.resolve()}:/submission/submission.csv:ro",
        "-v",
        f"{output_dir.resolve()}:/output",
        SUBMISSION_CHECKER_IMAGE,
        "-s",
        "/submission/submission.csv",
        "-d",
        "/output",
    ]

    container_id = None
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n=== Checker run started at {datetime.utcnow().isoformat()}Z ===\n")
        log_file.write("Command: " + " ".join(docker_cmd) + "\n")
        log_file.flush()
        try:
            start = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
            container_id = start.stdout.strip()
            log_file.write(f"Container ID: {container_id}\n")
            log_file.flush()
            with SessionLocal() as db:
                submission = db.get(Submission, submission_id)
                if submission:
                    submission.checker_container_id = container_id
                    submission.checker_exit_code = None
                    db.commit()

            logs_proc = subprocess.Popen(["docker", "logs", "-f", container_id], stdout=log_file, stderr=log_file)
            wait_result = subprocess.run(["docker", "wait", container_id], capture_output=True, text=True, check=False)
            if logs_proc.poll() is None:
                logs_proc.wait(timeout=15)

            exit_code = None
            if wait_result.stdout.strip().isdigit():
                exit_code = int(wait_result.stdout.strip())
            else:
                log_file.write(f"docker wait output: {wait_result.stdout}\n")
                if wait_result.stderr:
                    log_file.write(f"docker wait stderr: {wait_result.stderr}\n")

            with SessionLocal() as db:
                submission = db.get(Submission, submission_id)
                if submission:
                    submission.checker_exit_code = exit_code if exit_code is not None else 1
                    submission.checker_container_id = None
                    db.commit()

            log_file.write(f"Exit code: {exit_code}\n")
        except Exception as exc:
            log_file.write(f"Checker launch failed: {exc}\n")
            with SessionLocal() as db:
                submission = db.get(Submission, submission_id)
                if submission:
                    submission.checker_exit_code = 1
                    submission.checker_container_id = None
                    db.commit()
        finally:
            log_file.write(f"=== Checker run finished at {datetime.utcnow().isoformat()}Z ===\n")


def trigger_submission_checker(submission_id: int, marker_bytes: bytes, reset_output: bool = False) -> None:
    marker_path = submission_marker_file_path(submission_id)
    output_dir = submission_output_dir(submission_id)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    if reset_output and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path.write_bytes(marker_bytes)

    with SessionLocal() as db:
        submission = db.get(Submission, submission_id)
        if submission:
            submission.checker_exit_code = None
            submission.checker_container_id = "starting..."
            db.commit()

    worker = threading.Thread(target=run_submission_checker_in_background, args=(submission_id,), daemon=True)
    worker.start()


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


def sign_admin_value(username: str) -> str:
    raw = username.encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return f"{username}.{sig}"


def is_valid_admin_cookie(cookie_value: str | None) -> bool:
    if not cookie_value or "." not in cookie_value:
        return False
    username, sig = cookie_value.split(".", 1)
    if username != PANEL_ADMIN:
        return False
    expected = hmac.new(SECRET_KEY.encode("utf-8"), username.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


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


def admin_login_form(error: str = "") -> str:
    error_html = f'<div class="error">{error}</div>' if error else ""
    return page_template(
        "Admin Login",
        f"""
        <div class="header">Admin Login</div>
        <div class="content">
          {error_html}
          <form method="post" action="/admin/login">
            <label for="username">Username</label>
            <input id="username" name="username" type="text" required />

            <label for="password">Password</label>
            <input id="password" name="password" type="password" required />

            <button type="submit">Login</button>
          </form>
          <a class="link" href="/">Back to portal</a>
        </div>
        """,
    )


def require_admin(request: Request) -> bool:
    return is_valid_admin_cookie(request.cookies.get("admin_session"))


def subscribers_form(rows: str, error: str = "") -> str:
    error_html = f'<div class="error">{error}</div>' if error else ""
    return page_template(
        "Subscribers",
        f"""
        <div class="header">Subscribers</div>
        <div class="content">
          <a class="link" style="margin-top:0" href="/admin">← Back to admin</a>
          {error_html}
          <table style="width:100%; border-collapse: collapse; margin-top: 12px;">
            <thead>
              <tr>
                <th style="text-align:left; border-bottom:1px solid #c4cfdb; padding:8px;">Email</th>
                <th style="text-align:left; border-bottom:1px solid #c4cfdb; padding:8px; width:120px;">Action</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>

          <h3 style="margin-top:20px;">Add subscriber</h3>
          <form method="post" action="/admin/subscribers/add">
            <label for="subscriber_email">Email</label>
            <input id="subscriber_email" name="email" type="email" required />
            <button type="submit">Add Subscriber</button>
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
        success_dialog = ""
        if request.query_params.get("submission") == "success":
            success_dialog = "<script>alert(\"Submission Successful! We'll get back to you in a few days\");</script>"
        return HTMLResponse(
            page_template(
                "Panel Submission Portal",
                f"""
                <div class=\"header\">Organisation: {html.escape(user.organisation.name)} </div>
                <div class=\"content\">
                  <div class=\"top-actions\">
                    <div>
                      <h2>Panel Submission Portal</h2>
                      <p>Welcome {html.escape(user.email)}</p>
                      <p class=\"muted\">Logged into your organisation workspace.</p>
                    </div>
                    <form method=\"post\" action=\"/logout\" style=\"margin:0\">
                      <button type=\"submit\" class=\"logout\">Logout</button>
                    </form>
                  </div>
                  <form method=\"get\" action=\"/marker-submission\">
                    <button type=\"submit\">Submit Marker Panel</button>
                  </form>
                  <h3>Members</h3>
                  <ul>{member_items}</ul>
                </div>
                {success_dialog}
                """,
            )
        )


def require_user(request: Request) -> User | None:
    user_id = parse_session_value(request.cookies.get("session"))
    if user_id is None:
        return None
    with SessionLocal() as db:
        return db.get(User, user_id)


@app.get("/marker-template.csv")
def marker_template() -> HTMLResponse:
    return HTMLResponse(content=EXAMPLE_MARKER_FILE, media_type="text/csv")


@app.get("/marker-submission", response_class=HTMLResponse)
def marker_submission_page(request: Request) -> Response:
    user = require_user(request)
    if user is None:
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(
        page_template(
            "Panel Submission Portal",
            """
            <div class="header">Submit Marker Panel</div>
            <div class="content">
              <p class="muted">Upload a CSV file with marker panel data.</p>
              <p>
                Need an example file?
                <a class="link" style="margin-top:0" href="/marker-template.csv" download>Download sample CSV</a>
              </p>
              <form method="post" action="/marker-submission/validate" enctype="multipart/form-data">
                <label for="marker_file">Marker CSV file</label>
                <input id="marker_file" name="marker_file" type="file" accept=".csv,text/csv" required />
                <button type="submit">Validate File</button>
              </form>
            </div>
            """,
        )
    )


@app.post("/marker-submission/validate", response_class=HTMLResponse)
async def validate_marker_file(
    request: Request,
    marker_file: UploadFile = File(...),
) -> Response:
    user = require_user(request)
    if user is None:
        return RedirectResponse(url="/", status_code=303)

    file_bytes = await marker_file.read()
    try:
        decoded = file_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(decoded))
        header = next(reader)
    except Exception:
        return HTMLResponse(
            page_template(
                "Validation Result",
                """
                <div class="header">File Validation Output</div>
                <div class="content">
                  <div class="error">Could not parse the uploaded file as CSV.</div>
                  <a class="link" href="/marker-submission">Back to upload</a>
                </div>
                """,
            ),
            status_code=400,
        )

    normalized_header = {column.strip() for column in header}
    missing = sorted(REQUIRED_MARKER_COLUMNS - normalized_header)
    if missing:
        missing_items = "".join(f"<li>{html.escape(column)}</li>" for column in missing)
        return HTMLResponse(
            page_template(
                "Validation Result",
                f"""
                <div class="header">File Validation Output</div>
                <div class="content">
                  <div class="error">Missing required columns.</div>
                  <h3>Missing Columns</h3>
                  <ul>{missing_items}</ul>
                  <h3>Detected Columns</h3>
                  <p>{html.escape(', '.join(header))}</p>
                  <a class="link" href="/marker-submission">Back to upload</a>
                </div>
                """,
            ),
            status_code=400,
        )

    file_b64 = base64.b64encode(file_bytes).decode("utf-8")
    return HTMLResponse(
        page_template(
            "Submission Contacts",
            f"""
            <div class="header">Submission Contacts</div>
            <div class="content">
              <form method="post" action="/marker-submission/submit">
                <input type="hidden" name="file_name" value="{html.escape(marker_file.filename or 'marker_panel.csv')}" />
                <input type="hidden" name="file_b64" value="{html.escape(file_b64)}" />

                <label>Project Coordinator(s)</label>
                <div class="row">
                  <input name="project_coordinator_name" type="text" placeholder="Name" required />
                  <input name="project_coordinator_email" type="email" placeholder="Email" required />
                </div>

                <label>Marker Design Contact(s)</label>
                <div class="row">
                  <input name="marker_design_contact_name" type="text" placeholder="Name" required />
                  <input name="marker_design_contact_email" type="email" placeholder="Email" required />
                </div>

                <label>Contact(s) for receiving product name and custom code</label>
                <div class="row">
                  <input name="product_contact_name" type="text" placeholder="Name" required />
                  <input name="product_contact_email" type="email" placeholder="Email" required />
                </div>

                <label>Contact(s) for the TG</label>
                <div class="row">
                  <input name="tg_contact_name" type="text" placeholder="Name" required />
                  <input name="tg_contact_email" type="email" placeholder="Email" required />
                </div>

                <button type="submit">Submit</button>
              </form>
            </div>
            """,
        )
    )


@app.post("/marker-submission/submit")
def submit_marker_panel(
    request: Request,
    file_name: str = Form(...),
    file_b64: str = Form(...),
    project_coordinator_name: str = Form(...),
    project_coordinator_email: str = Form(...),
    marker_design_contact_name: str = Form(...),
    marker_design_contact_email: str = Form(...),
    product_contact_name: str = Form(...),
    product_contact_email: str = Form(...),
    tg_contact_name: str = Form(...),
    tg_contact_email: str = Form(...),
) -> RedirectResponse:
    user = require_user(request)
    if user is None:
        return RedirectResponse(url="/", status_code=303)

    submission = Submission(
        file_name=file_name,
        file_blob=base64.b64decode(file_b64.encode("utf-8")),
        project_coordinator_name=project_coordinator_name.strip(),
        project_coordinator_email=project_coordinator_email.strip(),
        marker_design_contact_name=marker_design_contact_name.strip(),
        marker_design_contact_email=marker_design_contact_email.strip(),
        product_contact_name=product_contact_name.strip(),
        product_contact_email=product_contact_email.strip(),
        tg_contact_name=tg_contact_name.strip(),
        tg_contact_email=tg_contact_email.strip(),
    )
    with SessionLocal() as db:
        db.add(submission)
        db.commit()
        db.refresh(submission)
        subscribers = db.scalars(select(Subscriber).order_by(Subscriber.email)).all()

    trigger_submission_checker(submission.id, submission.file_blob)

    submission_url = f"{APP_BASE_URL.rstrip('/')}/admin/submissions/{quote(str(submission.id))}"
    recipient_emails = [subscriber.email for subscriber in subscribers]
    send_submission_notification(recipient_emails, submission.id, submission_url)

    return RedirectResponse(url="/?submission=success", status_code=303)


@app.post("/login")
def login(email: str = Form(...), password: str = Form(...), organisation_id: int = Form(...)) -> Response:
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


@app.post("/register")
def register(
    email: str = Form(...),
    password: str = Form(...),
    organisation_id: str = Form(...),
    new_organisation_name: str = Form(""),
) -> Response:
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


@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request) -> HTMLResponse:
    if not require_admin(request):
        return HTMLResponse(admin_login_form())

    with SessionLocal() as db:
        submissions = db.scalars(select(Submission).order_by(Submission.date_submitted.desc())).all()

    rows = "".join(
        (
            f'<tr onclick="window.location=\'/admin/submissions/{submission.id}\'">'
            f"<td>{submission.id}</td>"
            f"<td>{html.escape(submission.file_name)}</td>"
            f"<td>{html.escape(submission.project_coordinator_name)}</td>"
            f"<td>{html.escape(submission.project_coordinator_email)}</td>"
            f"<td>{submission.date_submitted.strftime('%Y-%m-%d %H:%M:%S')}</td>"
            "</tr>"
        )
        for submission in submissions
    )
    if not rows:
        rows = '<tr><td colspan="5" class="muted">No submissions yet.</td></tr>'

    return HTMLResponse(
        page_template(
            "Admin Submissions",
            f"""
            <div class="header">Admin: Submissions</div>
            <div class="content">
              <div class="top-actions">
                <h2 style="margin:0">Marker Panel Submissions</h2>
                <a class="link" style="margin-top:0" href="/admin/subscribers">Subscribers</a>
                <form method="post" action="/admin/logout" style="margin:0">
                  <button type="submit" class="logout">Logout</button>
                </form>
              </div>
              <table style="width:100%; border-collapse: collapse;">
                <thead>
                  <tr>
                    <th style="text-align:left; border-bottom:1px solid #c4cfdb; padding:8px;">ID</th>
                    <th style="text-align:left; border-bottom:1px solid #c4cfdb; padding:8px;">File Name</th>
                    <th style="text-align:left; border-bottom:1px solid #c4cfdb; padding:8px;">Coordinator</th>
                    <th style="text-align:left; border-bottom:1px solid #c4cfdb; padding:8px;">Coordinator Email</th>
                    <th style="text-align:left; border-bottom:1px solid #c4cfdb; padding:8px;">Date Submitted</th>
                  </tr>
                </thead>
                <tbody>
                  {rows}
                </tbody>
              </table>
              <style>
                tbody tr {{ cursor: pointer; }}
                tbody tr:hover {{ background: #f3f7ff; }}
                td {{ padding: 8px; border-bottom: 1px solid #e3e9f0; }}
              </style>
            </div>
            """,
        )
    )


@app.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)) -> Response:
    if not (
        hmac.compare_digest(username.strip(), PANEL_ADMIN)
        and hmac.compare_digest(password, PANEL_ADMIN_PW)
    ):
        return HTMLResponse(admin_login_form("Invalid admin credentials."), status_code=401)

    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie("admin_session", sign_admin_value(PANEL_ADMIN), httponly=True, samesite="lax")
    return response


@app.post("/admin/logout")
def admin_logout() -> RedirectResponse:
    response = RedirectResponse(url="/admin", status_code=303)
    response.delete_cookie("admin_session")
    return response


@app.get("/admin/subscribers", response_class=HTMLResponse)
def admin_subscribers(request: Request) -> Response:
    if not require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    with SessionLocal() as db:
        subscribers = db.scalars(select(Subscriber).order_by(Subscriber.email)).all()

    rows = "".join(
        f"<tr><td style='padding:8px; border-bottom:1px solid #e3e9f0;'>{html.escape(sub.email)}</td>"
        f"<td style='padding:8px; border-bottom:1px solid #e3e9f0;'><form method='post' action='/admin/subscribers/remove' style='margin:0;'><input type='hidden' name='subscriber_id' value='{sub.id}' /><button type='submit' style='margin-top:0;'>Remove</button></form></td></tr>"
        for sub in subscribers
    )
    if not rows:
        rows = '<tr><td colspan="2" class="muted" style="padding:8px;">No subscribers configured.</td></tr>'

    return HTMLResponse(subscribers_form(rows))


@app.post("/admin/subscribers/add")
def admin_add_subscriber(request: Request, email: str = Form(...)) -> Response:
    if not require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    normalized_email = email.strip().lower()
    with SessionLocal() as db:
        exists = db.scalar(select(Subscriber).where(Subscriber.email == normalized_email))
        if exists:
            subscribers = db.scalars(select(Subscriber).order_by(Subscriber.email)).all()
            rows = "".join(
                f"<tr><td style='padding:8px; border-bottom:1px solid #e3e9f0;'>{html.escape(sub.email)}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #e3e9f0;'><form method='post' action='/admin/subscribers/remove' style='margin:0;'><input type='hidden' name='subscriber_id' value='{sub.id}' /><button type='submit' style='margin-top:0;'>Remove</button></form></td></tr>"
                for sub in subscribers
            )
            return HTMLResponse(subscribers_form(rows, "Subscriber already exists."), status_code=400)

        db.add(Subscriber(email=normalized_email))
        db.commit()

    return RedirectResponse(url="/admin/subscribers", status_code=303)


@app.post("/admin/subscribers/remove")
def admin_remove_subscriber(request: Request, subscriber_id: int = Form(...)) -> Response:
    if not require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    with SessionLocal() as db:
        subscriber = db.get(Subscriber, subscriber_id)
        if subscriber:
            db.delete(subscriber)
            db.commit()

    return RedirectResponse(url="/admin/subscribers", status_code=303)


@app.get("/admin/submissions/{submission_id}", response_class=HTMLResponse)
def admin_submission_detail(request: Request, submission_id: int) -> Response:
    if not require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    with SessionLocal() as db:
        submission = db.get(Submission, submission_id)

    if not submission:
        return HTMLResponse(
            page_template(
                "Not Found",
                """
                <div class="header">Submission Not Found</div>
                <div class="content">
                  <p class="error">The requested submission does not exist.</p>
                  <a class="link" href="/admin">Back to submissions</a>
                </div>
                """,
            ),
            status_code=404,
        )

    if submission.checker_container_id:
        checker_html = (
            f'<p style="color:#a67700;font-weight:700;">Running container: {html.escape(submission.checker_container_id)}</p>'
        )
    elif submission.checker_exit_code is None:
        checker_html = '<p class="muted">Checker has not run yet.</p>'
    elif submission.checker_exit_code == 0:
        checker_html = '<p style="color:#0f7a2a;font-weight:700;">✅ Checker completed successfully (exit code 0).</p>'
    else:
        checker_html = (
            f'<p style="color:#a11717;font-weight:700;">❌ Checker failed (exit code {submission.checker_exit_code}).</p>'
        )

    output_files = list_submission_output_files(submission.id)
    if output_files:
        files_html = "<ul>" + "".join(
            f'<li><a class="link" style="margin-top:0" href="/admin/submissions/{submission.id}/artifacts/{quote(path, safe="")}">{html.escape(path)}</a></li>'
            for path in output_files
        ) + "</ul>"
    else:
        files_html = '<p class="muted">No output files found yet.</p>'

    return HTMLResponse(
        page_template(
            f"Submission {submission.id}",
            f"""
            <div class="header">Submission #{submission.id}</div>
            <div class="content">
              <a class="link" style="margin-top:0" href="/admin">← Back to submissions</a>
              <form>
                <label>File Name</label>
                <input type="text" value="{html.escape(submission.file_name)}" readonly />

                <label>Date Submitted</label>
                <input type="text" value="{submission.date_submitted.strftime('%Y-%m-%d %H:%M:%S')}" readonly />

                <label>Project Coordinator Name</label>
                <input type="text" value="{html.escape(submission.project_coordinator_name)}" readonly />

                <label>Project Coordinator Email</label>
                <input type="text" value="{html.escape(submission.project_coordinator_email)}" readonly />

                <label>Marker Design Contact Name</label>
                <input type="text" value="{html.escape(submission.marker_design_contact_name)}" readonly />

                <label>Marker Design Contact Email</label>
                <input type="text" value="{html.escape(submission.marker_design_contact_email)}" readonly />

                <label>Product Contact Name</label>
                <input type="text" value="{html.escape(submission.product_contact_name)}" readonly />

                <label>Product Contact Email</label>
                <input type="text" value="{html.escape(submission.product_contact_email)}" readonly />

                <label>TG Contact Name</label>
                <input type="text" value="{html.escape(submission.tg_contact_name)}" readonly />

                <label>TG Contact Email</label>
                <input type="text" value="{html.escape(submission.tg_contact_email)}" readonly />
              </form>
              <a class="link" href="/admin/submissions/{submission.id}/marker-file" download>Download marker file</a>
              <h3 style="margin-top:22px;">Submission checker</h3>
              {checker_html}
              <form method="post" action="/admin/submissions/{submission.id}/rerun" style="margin-top:10px;">
                <button type="submit">Re-run checker (wipe existing output)</button>
              </form>
              <h3 style="margin-top:22px;">Output files</h3>
              {files_html}
            </div>
            """,
        )
    )


@app.get("/admin/submissions/{submission_id}/artifacts/{artifact_path:path}")
def admin_download_submission_artifact(request: Request, submission_id: int, artifact_path: str) -> Response:
    if not require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    base_dir = submission_output_dir(submission_id).resolve()
    target = (base_dir / artifact_path).resolve()
    if base_dir not in target.parents and target != base_dir:
        return Response(status_code=400)
    if not target.exists() or not target.is_file():
        return Response(status_code=404)

    media_type = "application/octet-stream"
    if target.suffix.lower() in {".txt", ".log", ".csv"}:
        media_type = "text/plain"
    return Response(
        content=target.read_bytes(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{target.name}"'},
    )


@app.post("/admin/submissions/{submission_id}/rerun")
def admin_rerun_submission_checker(request: Request, submission_id: int) -> Response:
    if not require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    with SessionLocal() as db:
        submission = db.get(Submission, submission_id)
    if not submission:
        return Response(status_code=404)

    trigger_submission_checker(submission_id, submission.file_blob, reset_output=True)
    return RedirectResponse(url=f"/admin/submissions/{submission_id}", status_code=303)


@app.get("/admin/submissions/{submission_id}/marker-file")
def admin_download_marker_file(request: Request, submission_id: int) -> Response:
    if not require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    with SessionLocal() as db:
        submission = db.get(Submission, submission_id)
    if not submission:
        return Response(status_code=404)

    return Response(
        content=submission.file_blob,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{submission.file_name}"'},
    )
