import os
from datetime import date
from html import escape

import pymysql
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Codex Business App")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "codex_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "codex_app_password")
DB_NAME = os.getenv("DB_NAME", "codex_activity_app")


def get_connection(database: str | None = DB_NAME) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def ensure_schema() -> None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  name VARCHAR(255) NOT NULL,
                  description TEXT NOT NULL,
                  date_created DATE NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS members (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  first_name VARCHAR(120) NOT NULL,
                  middle_name VARCHAR(120) NULL,
                  last_name VARCHAR(120) NOT NULL,
                  phone VARCHAR(30) NULL,
                  email VARCHAR(255) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS project_members (
                  project_id INT NOT NULL,
                  member_id INT NOT NULL,
                  PRIMARY KEY (project_id, member_id),
                  CONSTRAINT fk_pm_project FOREIGN KEY (project_id)
                    REFERENCES projects(id) ON DELETE CASCADE,
                  CONSTRAINT fk_pm_member FOREIGN KEY (member_id)
                    REFERENCES members(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )


@app.on_event("startup")
def startup() -> None:
    ensure_schema()


def render_page(title: str, content: str, subtitle: str = "Codex built this!") -> str:
    return f"""
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{escape(title)}</title>
    <style>
      :root {{
        --bg: #f3f6fb;
        --card: #ffffff;
        --text: #1f2a44;
        --muted: #64748b;
        --border: #d7deea;
        --primary: #2f6fed;
        --primary-dark: #2457bb;
        --danger: #cc3344;
        --danger-dark: #9f2533;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: Inter, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
        background: linear-gradient(180deg, #f7f9fd 0%, var(--bg) 100%);
        color: var(--text);
      }}
      .container {{ max-width: 1080px; margin: 36px auto; padding: 0 20px; }}
      .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 16px; box-shadow: 0 8px 24px rgba(31, 42, 68, 0.06); overflow: hidden; margin-bottom: 16px; }}
      .header {{ padding: 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
      h1 {{ margin: 0; font-size: 1.4rem; }}
      h2 {{ margin: 0 0 12px; font-size: 1.1rem; }}
      .subtitle {{ margin: 4px 0 0; color: var(--muted); font-size: 0.95rem; }}
      .content {{ padding: 20px 24px 24px; }}
      .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
      button, .btn {{ border: 0; border-radius: 10px; padding: 10px 16px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; }}
      .primary {{ background: var(--primary); color: white; }}
      .primary:hover {{ background: var(--primary-dark); }}
      .danger {{ background: var(--danger); color: white; }}
      .danger:hover {{ background: var(--danger-dark); }}
      .secondary {{ background: #e6eaf4; color: #2e405f; }}
      .small {{ padding: 6px 10px; font-size: 0.82rem; }}
      table {{ width: 100%; border-collapse: collapse; }}
      thead th {{ text-align: left; background: #eef3ff; color: #35507a; padding: 14px; font-size: 0.88rem; letter-spacing: 0.02em; text-transform: uppercase; }}
      tbody td {{ padding: 14px; border-top: 1px solid var(--border); vertical-align: top; }}
      .empty {{ text-align: center; color: var(--muted); padding: 30px; }}
      .menu {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
      .tile-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
      .tile {{ border: 1px solid var(--border); border-radius: 12px; padding: 18px; background: #fbfcff; text-decoration: none; color: var(--text); }}
      .tile h3 {{ margin: 0 0 8px; }}
      .tile p {{ margin: 0; color: var(--muted); }}
      a.row-link {{ color: var(--primary); text-decoration: none; font-weight: 600; }}
      a.row-link:hover {{ text-decoration: underline; }}
      dialog {{ border: 1px solid var(--border); border-radius: 12px; width: 520px; max-width: 95vw; }}
      dialog::backdrop {{ background: rgba(9, 20, 40, 0.45); }}
      .field {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }}
      .field input, .field textarea, .field select {{ border: 1px solid #b7c6dd; border-radius: 8px; padding: 10px; font: inherit; }}
      .dialog-actions {{ display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }}
      .kv {{ display: grid; grid-template-columns: 160px 1fr; gap: 8px 14px; }}
      .muted {{ color: var(--muted); }}
    </style>
  </head>
  <body>
    <div class=\"container\">
      <div class=\"card\">
        <div class=\"header\">
          <div>
            <h1>{escape(title)}</h1>
            <p class=\"subtitle\">{escape(subtitle)}</p>
          </div>
        </div>
        <div class=\"content\">{content}</div>
      </div>
    </div>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    content = """
    <div class=\"tile-grid\">
      <a class=\"tile\" href=\"/projects\">
        <h3>Projects</h3>
        <p>Manage projects, open project detail pages, and assign project members.</p>
      </a>
      <a class=\"tile\" href=\"/members\">
        <h3>Members</h3>
        <p>Manage member records and browse assigned projects.</p>
      </a>
    </div>
    """
    return render_page("Business Dashboard", content)


@app.get("/projects", response_class=HTMLResponse)
def projects_page() -> str:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, description, date_created FROM projects ORDER BY date_created DESC, id DESC")
            projects = cursor.fetchall()

    rows = "\n".join(
        f"""
        <tr>
          <td><a class=\"row-link\" href=\"/projects/{p['id']}\">{escape(p['name'])}</a></td>
          <td>{escape(p['description'])}</td>
          <td>{p['date_created']}</td>
          <td>
            <form method=\"post\" action=\"/projects/{p['id']}/delete\" onsubmit=\"return confirm('Delete this project?');\">
              <button class=\"danger small\" type=\"submit\">Delete</button>
            </form>
          </td>
        </tr>
        """
        for p in projects
    )
    if not rows:
        rows = "<tr><td colspan='4' class='empty'>No projects yet.</td></tr>"

    today = date.today().isoformat()
    content = f"""
    <div class=\"menu\">
      <a class=\"btn secondary\" href=\"/\">Back to Home</a>
      <a class=\"btn secondary\" href=\"/members\">Members</a>
    </div>
    <div style=\"height:12px\"></div>
    <div class=\"actions\">
      <button class=\"primary\" onclick=\"document.getElementById('addProjectDialog').showModal()\">Add Project</button>
      <button class=\"danger\" onclick=\"document.getElementById('deleteProjectsDialog').showModal()\">Delete All</button>
    </div>
    <div style=\"height:12px\"></div>
    <table>
      <thead><tr><th>Name</th><th>Description</th><th>Date Created</th><th>Actions</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>

    <dialog id=\"addProjectDialog\">
      <form method=\"post\" action=\"/projects\">
        <h3>Create Project</h3>
        <div class=\"field\"><label>Name</label><input name=\"name\" required maxlength=\"255\"/></div>
        <div class=\"field\"><label>Description</label><textarea name=\"description\" required rows=\"4\"></textarea></div>
        <div class=\"field\"><label>Date Created</label><input name=\"date_created\" type=\"date\" value=\"{today}\" required/></div>
        <div class=\"dialog-actions\">
          <button type=\"button\" class=\"secondary\" onclick=\"document.getElementById('addProjectDialog').close()\">Cancel</button>
          <button type=\"submit\" class=\"primary\">Create</button>
        </div>
      </form>
    </dialog>

    <dialog id=\"deleteProjectsDialog\">
      <form method=\"post\" action=\"/projects/delete-all\" onsubmit=\"return confirm('Delete ALL projects?');\">
        <h3>Delete All Projects</h3>
        <p class=\"muted\">This removes all projects and project-member assignments.</p>
        <div class=\"dialog-actions\">
          <button type=\"button\" class=\"secondary\" onclick=\"document.getElementById('deleteProjectsDialog').close()\">Cancel</button>
          <button type=\"submit\" class=\"danger\">Delete All</button>
        </div>
      </form>
    </dialog>
    """
    return render_page("Projects", content)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: int) -> str:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, description, date_created FROM projects WHERE id=%s", (project_id,))
            project = cursor.fetchone()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            cursor.execute(
                """
                SELECT m.id, m.first_name, m.middle_name, m.last_name, m.email
                FROM members m
                JOIN project_members pm ON pm.member_id = m.id
                WHERE pm.project_id = %s
                ORDER BY m.last_name, m.first_name
                """,
                (project_id,),
            )
            assigned = cursor.fetchall()

            cursor.execute(
                """
                SELECT m.id, m.first_name, m.middle_name, m.last_name, m.email
                FROM members m
                WHERE NOT EXISTS (
                    SELECT 1 FROM project_members pm
                    WHERE pm.project_id = %s AND pm.member_id = m.id
                )
                ORDER BY m.last_name, m.first_name
                """,
                (project_id,),
            )
            available = cursor.fetchall()

    assigned_rows = "\n".join(
        f"<tr><td><a class='row-link' href='/members/{m['id']}'>{escape(m['first_name'])} {escape(m['last_name'])}</a></td><td>{escape(m.get('middle_name') or '-')}</td><td>{escape(m['email'])}</td></tr>"
        for m in assigned
    )
    if not assigned_rows:
        assigned_rows = "<tr><td colspan='3' class='empty'>No members assigned.</td></tr>"

    options = "\n".join(
        f"<option value='{m['id']}'>{escape(m['first_name'])} {escape(m['last_name'])} ({escape(m['email'])})</option>"
        for m in available
    )

    content = f"""
    <div class=\"menu\">
      <a class=\"btn secondary\" href=\"/\">Home</a>
      <a class=\"btn secondary\" href=\"/projects\">Back to Projects</a>
      <a class=\"btn secondary\" href=\"/members\">Members</a>
    </div>
    <div style=\"height:14px\"></div>
    <h2>Project Details</h2>
    <div class=\"kv\">
      <strong>Name</strong><span>{escape(project['name'])}</span>
      <strong>Description</strong><span>{escape(project['description'])}</span>
      <strong>Date Created</strong><span>{project['date_created']}</span>
    </div>
    <div style=\"height:20px\"></div>
    <h2>Members</h2>
    <div class=\"actions\">
      <button class=\"primary\" onclick=\"document.getElementById('addMemberLookupDialog').showModal()\">Add Member via Lookup</button>
    </div>
    <div style=\"height:10px\"></div>
    <table>
      <thead><tr><th>First + Last Name</th><th>Middle Name</th><th>Email</th></tr></thead>
      <tbody>{assigned_rows}</tbody>
    </table>

    <dialog id=\"addMemberLookupDialog\">
      <form method=\"post\" action=\"/projects/{project_id}/members\">
        <h3>Add Member via Lookup</h3>
        <div class=\"field\"><label>Member</label>
          <select name=\"member_id\" {'required' if available else 'disabled'}>
            {options if options else '<option>No available members</option>'}
          </select>
        </div>
        <div class=\"dialog-actions\">
          <button type=\"button\" class=\"secondary\" onclick=\"document.getElementById('addMemberLookupDialog').close()\">Cancel</button>
          <button type=\"submit\" class=\"primary\" {'disabled' if not available else ''}>Add</button>
        </div>
      </form>
    </dialog>
    """
    return render_page(f"Project #{project_id}", content)


@app.post("/projects")
def create_project(
    name: str = Form(...),
    description: str = Form(...),
    date_created: date | None = Form(None),
) -> RedirectResponse:
    if date_created is None:
        date_created = date.today()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO projects (name, description, date_created) VALUES (%s, %s, %s)",
                (name.strip(), description.strip(), date_created),
            )
    return RedirectResponse(url="/projects", status_code=303)


@app.post("/projects/{project_id}/delete")
def delete_project(project_id: int) -> RedirectResponse:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
    return RedirectResponse(url="/projects", status_code=303)


@app.post("/projects/delete-all")
def delete_all_projects() -> RedirectResponse:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM projects")
    return RedirectResponse(url="/projects", status_code=303)


@app.post("/projects/{project_id}/members")
def add_member_to_project(project_id: int, member_id: int = Form(...)) -> RedirectResponse:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Project not found")
            cursor.execute("SELECT id FROM members WHERE id = %s", (member_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Member not found")
            cursor.execute(
                "INSERT IGNORE INTO project_members (project_id, member_id) VALUES (%s, %s)",
                (project_id, member_id),
            )
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@app.get("/members", response_class=HTMLResponse)
def members_page() -> str:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, first_name, middle_name, last_name, phone, email FROM members ORDER BY last_name, first_name"
            )
            members = cursor.fetchall()

    rows = "\n".join(
        f"""
        <tr>
          <td><a class='row-link' href='/members/{m['id']}'>{escape(m['first_name'])}</a></td>
          <td>{escape(m.get('middle_name') or '')}</td>
          <td><a class='row-link' href='/members/{m['id']}'>{escape(m['last_name'])}</a></td>
          <td>{escape(m.get('phone') or '')}</td>
          <td>{escape(m['email'])}</td>
          <td>
            <form method=\"post\" action=\"/members/{m['id']}/delete\" onsubmit=\"return confirm('Delete this member?');\">
              <button class=\"danger small\" type=\"submit\">Delete</button>
            </form>
          </td>
        </tr>
        """
        for m in members
    )
    if not rows:
        rows = "<tr><td colspan='6' class='empty'>No members yet.</td></tr>"

    content = f"""
    <div class=\"menu\">
      <a class=\"btn secondary\" href=\"/\">Home</a>
      <a class=\"btn secondary\" href=\"/projects\">Projects</a>
    </div>
    <div style=\"height:12px\"></div>
    <div class=\"actions\">
      <button class=\"primary\" onclick=\"document.getElementById('addMemberDialog').showModal()\">Add Member</button>
      <button class=\"danger\" onclick=\"document.getElementById('deleteMembersDialog').showModal()\">Delete All</button>
    </div>
    <div style=\"height:12px\"></div>
    <table>
      <thead><tr><th>First-name</th><th>Middle-name</th><th>Last-name</th><th>Phone</th><th>Email</th><th>Actions</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>

    <dialog id=\"addMemberDialog\">
      <form method=\"post\" action=\"/members\">
        <h3>Create Member</h3>
        <div class=\"field\"><label>First-name</label><input name=\"first_name\" required maxlength=\"120\"/></div>
        <div class=\"field\"><label>Middle-name (optional)</label><input name=\"middle_name\" maxlength=\"120\"/></div>
        <div class=\"field\"><label>Last-name</label><input name=\"last_name\" required maxlength=\"120\"/></div>
        <div class=\"field\"><label>Phone (optional)</label><input name=\"phone\" maxlength=\"30\"/></div>
        <div class=\"field\"><label>Email</label><input type=\"email\" name=\"email\" required maxlength=\"255\"/></div>
        <div class=\"dialog-actions\">
          <button type=\"button\" class=\"secondary\" onclick=\"document.getElementById('addMemberDialog').close()\">Cancel</button>
          <button type=\"submit\" class=\"primary\">Create</button>
        </div>
      </form>
    </dialog>

    <dialog id=\"deleteMembersDialog\">
      <form method=\"post\" action=\"/members/delete-all\" onsubmit=\"return confirm('Delete ALL members?');\">
        <h3>Delete All Members</h3>
        <p class=\"muted\">This removes all members and project-member assignments.</p>
        <div class=\"dialog-actions\">
          <button type=\"button\" class=\"secondary\" onclick=\"document.getElementById('deleteMembersDialog').close()\">Cancel</button>
          <button type=\"submit\" class=\"danger\">Delete All</button>
        </div>
      </form>
    </dialog>
    """
    return render_page("Members", content)


@app.post("/members")
def create_member(
    first_name: str = Form(...),
    middle_name: str = Form(""),
    last_name: str = Form(...),
    phone: str = Form(""),
    email: str = Form(...),
) -> RedirectResponse:
    middle = middle_name.strip() or None
    phone_val = phone.strip() or None
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO members (first_name, middle_name, last_name, phone, email)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (first_name.strip(), middle, last_name.strip(), phone_val, email.strip()),
            )
    return RedirectResponse(url="/members", status_code=303)


@app.post("/members/{member_id}/delete")
def delete_member(member_id: int) -> RedirectResponse:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM members WHERE id = %s", (member_id,))
    return RedirectResponse(url="/members", status_code=303)


@app.post("/members/delete-all")
def delete_all_members() -> RedirectResponse:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM members")
    return RedirectResponse(url="/members", status_code=303)


@app.get("/members/{member_id}", response_class=HTMLResponse)
def member_detail(member_id: int) -> str:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, first_name, middle_name, last_name, phone, email FROM members WHERE id=%s",
                (member_id,),
            )
            member = cursor.fetchone()
            if not member:
                raise HTTPException(status_code=404, detail="Member not found")

            cursor.execute(
                """
                SELECT p.id, p.name, p.description, p.date_created
                FROM projects p
                JOIN project_members pm ON pm.project_id = p.id
                WHERE pm.member_id = %s
                ORDER BY p.date_created DESC, p.id DESC
                """,
                (member_id,),
            )
            projects = cursor.fetchall()

    project_rows = "\n".join(
        f"<tr><td><a class='row-link' href='/projects/{p['id']}'>{escape(p['name'])}</a></td><td>{escape(p['description'])}</td><td>{p['date_created']}</td></tr>"
        for p in projects
    )
    if not project_rows:
        project_rows = "<tr><td colspan='3' class='empty'>This member has no projects.</td></tr>"

    content = f"""
    <div class=\"menu\">
      <a class=\"btn secondary\" href=\"/\">Home</a>
      <a class=\"btn secondary\" href=\"/members\">Back to Members</a>
      <a class=\"btn secondary\" href=\"/projects\">Projects</a>
    </div>
    <div style=\"height:14px\"></div>
    <h2>Member Details</h2>
    <div class=\"kv\">
      <strong>First-name</strong><span>{escape(member['first_name'])}</span>
      <strong>Middle-name</strong><span>{escape(member.get('middle_name') or '')}</span>
      <strong>Last-name</strong><span>{escape(member['last_name'])}</span>
      <strong>Phone</strong><span>{escape(member.get('phone') or '')}</span>
      <strong>Email</strong><span>{escape(member['email'])}</span>
    </div>
    <div style=\"height:20px\"></div>
    <h2>Projects</h2>
    <table>
      <thead><tr><th>Name</th><th>Description</th><th>Date Created</th></tr></thead>
      <tbody>{project_rows}</tbody>
    </table>
    """
    return render_page(f"Member #{member_id}", content)
