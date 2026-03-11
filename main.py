import html
import os
from datetime import date
from typing import Any

import mysql.connector
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Codex Activity App")


MENU = [("Home", "/"), ("Projects", "/projects"), ("Members", "/members"), ("Organization", "/organizations")]


def get_connection() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "codex_app"),
        password=os.getenv("DB_PASSWORD", "codex_password"),
        database=os.getenv("DB_NAME", "codex_activity"),
    )


def ensure_schema() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS organizations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            address TEXT NULL,
            abn VARCHAR(50) NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            date_created DATE NOT NULL,
            organization_id INT NULL,
            CONSTRAINT fk_projects_organization
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
                ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS organization_id INT NULL")
    cursor.execute(
        """
        ALTER TABLE projects
        ADD CONSTRAINT IF NOT EXISTS fk_projects_organization
        FOREIGN KEY (organization_id) REFERENCES organizations(id)
        ON DELETE SET NULL
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS members (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            middle_name VARCHAR(100) NULL,
            last_name VARCHAR(100) NOT NULL,
            phone VARCHAR(50) NULL,
            email VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    cursor.execute(
        """
        ALTER TABLE members
        MODIFY middle_name VARCHAR(100) NULL,
        MODIFY phone VARCHAR(50) NULL
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS project_members (
            project_id INT NOT NULL,
            member_id INT NOT NULL,
            PRIMARY KEY (project_id, member_id),
            CONSTRAINT fk_project_members_project
                FOREIGN KEY (project_id) REFERENCES projects(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_project_members_member
                FOREIGN KEY (member_id) REFERENCES members(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS organization_members (
            organization_id INT NOT NULL,
            member_id INT NOT NULL,
            PRIMARY KEY (organization_id, member_id),
            CONSTRAINT fk_org_members_organization
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_org_members_member
                FOREIGN KEY (member_id) REFERENCES members(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    conn.commit()
    cursor.close()
    conn.close()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return new_id


def execute_many(query: str, params: list[Any]) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    cursor.close()
    conn.close()


def page_shell(title: str, body: str, menu: list[tuple[str, str]] = MENU) -> str:
    nav_items = "".join(
        f"<a href='{html.escape(path)}'>{html.escape(label)}</a>" for label, path in menu
    )
    return f"""
<!doctype html>
<html lang='en'>
  <head>
    <meta charset='UTF-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1.0' />
    <title>{html.escape(title)}</title>
    <style>
      :root {{ --bg:#f3f6fb; --panel:#fff; --text:#111827; --muted:#6b7280; --line:#e5e7eb; --primary:#1f6feb; --primary-dark:#1557bf; --danger:#b42318; }}
      * {{ box-sizing: border-box; }}
      body {{ margin:0; background:var(--bg); color:var(--text); font-family:"Inter","Segoe UI",Arial,sans-serif; }}
      .container {{ max-width:1160px; margin:42px auto; padding:0 24px; }}
      .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; box-shadow:0 8px 24px rgba(15,23,42,.06); overflow:hidden; }}
      .menu {{ display:flex; gap:12px; padding:14px 24px; border-bottom:1px solid var(--line); background:#fbfcff; }}
      .menu a {{ color:var(--primary); text-decoration:none; font-weight:600; }}
      .menu a:hover {{ text-decoration:underline; }}
      .header {{ padding:24px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }}
      .title {{ margin:0; font-size:1.5rem; }}
      .subtitle {{ margin-top:6px; color:var(--muted); }}
      .actions {{ display:flex; gap:10px; }}
      button {{ border:none; border-radius:8px; padding:10px 16px; font-weight:600; cursor:pointer; }}
      .btn-primary {{ background:var(--primary); color:white; }}
      .btn-primary:hover {{ background:var(--primary-dark); }}
      .btn-danger {{ background:var(--danger); color:white; }}
      .table-wrap {{ padding:0 24px 24px; }}
      table {{ width:100%; border-collapse:collapse; margin-top:12px; }}
      th,td {{ padding:12px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
      th {{ color:var(--muted); font-size:.83rem; text-transform:uppercase; letter-spacing:.03em; }}
      .empty-row {{ text-align:center; color:var(--muted); padding:26px 10px; }}
      .tile-grid {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); padding:24px; }}
      .tile {{ border:1px solid var(--line); border-radius:12px; background:#fbfdff; padding:20px; text-decoration:none; color:inherit; }}
      .tile h3 {{ margin:0 0 8px; color:var(--primary); }}
      .tile:hover {{ border-color:#bfdbfe; box-shadow:0 4px 14px rgba(31,111,235,.15); }}
      .details {{ padding:24px; }}
      .detail-grid {{ display:grid; grid-template-columns:220px 1fr; gap:12px; margin-bottom:24px; }}
      .detail-label {{ color:var(--muted); font-weight:700; }}
      dialog {{ border:none; border-radius:12px; padding:0; width:min(620px,96%); }}
      dialog::backdrop {{ background:rgba(15,23,42,.45); }}
      .dialog-body {{ padding:20px; }}
      .field {{ display:flex; flex-direction:column; margin-bottom:14px; }}
      input,textarea,select {{ border:1px solid #d0d7de; border-radius:8px; padding:10px; font-size:.95rem; }}
      textarea {{ min-height:96px; resize:vertical; }}
      .dialog-actions {{ display:flex; justify-content:flex-end; gap:10px; }}
      .btn-secondary {{ background:#eef2f7; color:#344054; }}
    </style>
  </head>
  <body>
    <div class='container'>
      <div class='card'>
        <div class='menu'>{nav_items}</div>
        {body}
      </div>
    </div>
    <script>
      function openDialog(id) {{ document.getElementById(id).showModal(); }}
      function closeDialog(id) {{ document.getElementById(id).close(); }}
    </script>
  </body>
</html>
    """


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    ensure_schema()
    body = """
      <div class='header'><div><h1 class='title'>Codex Activity Portal</h1><div class='subtitle'>Business workspace landing page</div></div></div>
      <div class='tile-grid'>
        <a class='tile' href='/projects'><h3>Projects</h3><p>Browse, create, and manage projects.</p></a>
        <a class='tile' href='/members'><h3>Members</h3><p>Maintain member records and assignments.</p></a>
        <a class='tile' href='/organizations'><h3>Organization</h3><p>Manage organizations and related projects/members.</p></a>
      </div>
    """
    return HTMLResponse(page_shell("Home", body))


@app.get("/projects", response_class=HTMLResponse)
def projects_page() -> HTMLResponse:
    ensure_schema()
    projects = fetch_all(
        """
        SELECT p.id, p.name, p.description, p.date_created, o.name AS organization_name
        FROM projects p
        LEFT JOIN organizations o ON o.id = p.organization_id
        ORDER BY p.date_created DESC, p.id DESC
        """
    )
    organizations = fetch_all("SELECT id, name FROM organizations ORDER BY name")
    options = "".join(
        f"<option value='{o['id']}'>{html.escape(str(o['name']))}</option>" for o in organizations
    )
    rows = "".join(
        f"""
        <tr>
          <td><input type='checkbox' name='project_ids' value='{p['id']}' /></td>
          <td><a href='/projects/{p['id']}'>{html.escape(str(p['name']))}</a></td>
          <td>{html.escape(str(p['description']))}</td>
          <td>{html.escape(str(p['organization_name'] or ''))}</td>
          <td>{p['date_created']}</td>
        </tr>
        """
        for p in projects
    ) or "<tr><td colspan='5' class='empty-row'>No projects found.</td></tr>"

    body = f"""
      <div class='header'>
        <div><h1 class='title'>Projects</h1><div class='subtitle'>Project portfolio</div></div>
        <div class='actions'>
          <button class='btn-primary' type='button' onclick=\"openDialog('addProjectDialog')\">Add Project</button>
          <button class='btn-danger' type='submit' form='deleteProjectsForm'>Delete Selected</button>
        </div>
      </div>
      <div class='table-wrap'>
        <form id='deleteProjectsForm' method='post' action='/projects/delete'>
          <table>
            <thead><tr><th style='width:48px;'>Select</th><th>Name</th><th>Description</th><th>Organization</th><th>Date Created</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </form>
      </div>
      <dialog id='addProjectDialog'>
        <form method='post' action='/projects'>
          <div class='dialog-body'>
            <h2>Create New Project</h2>
            <div class='field'><label>Name</label><input name='name' maxlength='255' required /></div>
            <div class='field'><label>Description</label><textarea name='description' required></textarea></div>
            <div class='field'><label>Organization</label><select name='organization_id'><option value=''>None</option>{options}</select></div>
            <div class='field'><label>Date Created</label><input name='date_created' type='date' value='{date.today().isoformat()}' required /></div>
            <div class='dialog-actions'><button type='button' class='btn-secondary' onclick=\"closeDialog('addProjectDialog')\">Cancel</button><button type='submit' class='btn-primary'>Save Project</button></div>
          </div>
        </form>
      </dialog>
    """
    return HTMLResponse(page_shell("Projects", body))


@app.get("/organizations", response_class=HTMLResponse)
def organizations_page() -> HTMLResponse:
    ensure_schema()
    orgs = fetch_all("SELECT id, name, address, abn FROM organizations ORDER BY id DESC")
    rows = "".join(
        f"""
        <tr>
          <td><input type='checkbox' name='organization_ids' value='{o['id']}' /></td>
          <td><a href='/organizations/{o['id']}'>{html.escape(str(o['name']))}</a></td>
          <td>{html.escape(str(o['address'] or ''))}</td>
          <td>{html.escape(str(o['abn'] or ''))}</td>
        </tr>
        """
        for o in orgs
    ) or "<tr><td colspan='4' class='empty-row'>No organizations found.</td></tr>"
    body = f"""
      <div class='header'>
        <div><h1 class='title'>Organization</h1><div class='subtitle'>Organization directory</div></div>
        <div class='actions'>
          <button class='btn-primary' type='button' onclick=\"openDialog('addOrganizationDialog')\">Add Organization</button>
          <button class='btn-danger' type='submit' form='deleteOrganizationsForm'>Delete Selected</button>
        </div>
      </div>
      <div class='table-wrap'>
        <form id='deleteOrganizationsForm' method='post' action='/organizations/delete'>
          <table>
            <thead><tr><th style='width:48px;'>Select</th><th>Name</th><th>Address</th><th>ABN</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </form>
      </div>
      <dialog id='addOrganizationDialog'>
        <form method='post' action='/organizations'>
          <div class='dialog-body'>
            <h2>Create New Organization</h2>
            <div class='field'><label>Name</label><input name='name' maxlength='255' required /></div>
            <div class='field'><label>Address (optional)</label><textarea name='address'></textarea></div>
            <div class='field'><label>ABN (optional)</label><input name='abn' maxlength='50' /></div>
            <div class='dialog-actions'><button type='button' class='btn-secondary' onclick=\"closeDialog('addOrganizationDialog')\">Cancel</button><button type='submit' class='btn-primary'>Save Organization</button></div>
          </div>
        </form>
      </dialog>
    """
    return HTMLResponse(page_shell("Organization", body))


@app.get("/members", response_class=HTMLResponse)
def members_page() -> HTMLResponse:
    ensure_schema()
    members = fetch_all("SELECT id, first_name, middle_name, last_name, phone, email FROM members ORDER BY id DESC")
    rows = "".join(
        f"""
        <tr>
          <td><input type='checkbox' name='member_ids' value='{m['id']}' /></td>
          <td><a href='/members/{m['id']}'>{html.escape(str(m['first_name']))}</a></td>
          <td>{html.escape(str(m['middle_name'] or ''))}</td>
          <td>{html.escape(str(m['last_name']))}</td>
          <td>{html.escape(str(m['phone'] or ''))}</td>
          <td>{html.escape(str(m['email']))}</td>
        </tr>
        """
        for m in members
    ) or "<tr><td colspan='6' class='empty-row'>No members found.</td></tr>"
    body = f"""
      <div class='header'>
        <div><h1 class='title'>Members</h1><div class='subtitle'>Directory of project members</div></div>
        <div class='actions'>
          <button class='btn-primary' type='button' onclick=\"openDialog('addMemberDialog')\">Add Member</button>
          <button class='btn-danger' type='submit' form='deleteMembersForm'>Delete Selected</button>
        </div>
      </div>
      <div class='table-wrap'>
        <form id='deleteMembersForm' method='post' action='/members/delete'>
          <table>
            <thead><tr><th style='width:48px;'>Select</th><th>First-name</th><th>Middle-name</th><th>Last-name</th><th>Phone</th><th>Email</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </form>
      </div>
      <dialog id='addMemberDialog'>
        <form method='post' action='/members'>
          <div class='dialog-body'>
            <h2>Create New Member</h2>
            <div class='field'><label>First-name</label><input name='first_name' maxlength='100' required /></div>
            <div class='field'><label>Middle-name (optional)</label><input name='middle_name' maxlength='100' /></div>
            <div class='field'><label>Last-name</label><input name='last_name' maxlength='100' required /></div>
            <div class='field'><label>Phone (optional)</label><input name='phone' maxlength='50' /></div>
            <div class='field'><label>Email</label><input name='email' maxlength='255' required /></div>
            <div class='dialog-actions'><button type='button' class='btn-secondary' onclick=\"closeDialog('addMemberDialog')\">Cancel</button><button type='submit' class='btn-primary'>Save Member</button></div>
          </div>
        </form>
      </dialog>
    """
    return HTMLResponse(page_shell("Members", body))


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: int) -> HTMLResponse:
    ensure_schema()
    project = fetch_one(
        """
        SELECT p.id, p.name, p.description, p.date_created, o.id AS organization_id, o.name AS organization_name
        FROM projects p
        LEFT JOIN organizations o ON o.id = p.organization_id
        WHERE p.id = %s
        """,
        (project_id,),
    )
    if not project:
        return HTMLResponse("Project not found", status_code=404)

    project_members = fetch_all(
        """
        SELECT m.id, m.first_name, m.middle_name, m.last_name, m.email
        FROM project_members pm JOIN members m ON m.id = pm.member_id
        WHERE pm.project_id = %s ORDER BY m.first_name, m.last_name
        """,
        (project_id,),
    )
    available_members = fetch_all(
        """
        SELECT m.id, m.first_name, m.middle_name, m.last_name
        FROM members m
        WHERE m.id NOT IN (SELECT member_id FROM project_members WHERE project_id = %s)
        ORDER BY m.first_name, m.last_name
        """,
        (project_id,),
    )
    member_rows = "".join(
        f"<tr><td><a href='/members/{m['id']}'>{html.escape(m['first_name'])} {html.escape(m['middle_name'] or '')} {html.escape(m['last_name'])}</a></td><td>{html.escape(m['email'])}</td></tr>"
        for m in project_members
    ) or "<tr><td colspan='2' class='empty-row'>No members assigned.</td></tr>"
    options = "".join(
        f"<option value='{m['id']}'>{html.escape(m['first_name'])} {html.escape(m['middle_name'] or '')} {html.escape(m['last_name'])}</option>"
        for m in available_members
    )
    selector = f"""
      <form method='post' action='/projects/{project_id}/members' style='margin: 0 24px 18px;'>
        <div class='field'><label>Add Member (lookup)</label><select name='member_id' required><option value=''>Choose member</option>{options}</select></div>
        <button class='btn-primary' type='submit'>Add Member</button>
      </form>
    """ if available_members else "<div style='padding:0 24px 14px; color:#6b7280;'>All members are already assigned or no members exist.</div>"

    org_text = (
        f"<a href='/organizations/{project['organization_id']}'>{html.escape(str(project['organization_name']))}</a>"
        if project["organization_id"]
        else ""
    )
    body = f"""
      <div class='header'><div><h1 class='title'>Project: {html.escape(str(project['name']))}</h1><div class='subtitle'>Project detail</div></div></div>
      <div class='details'>
        <div class='detail-grid'>
          <div class='detail-label'>Name</div><div>{html.escape(str(project['name']))}</div>
          <div class='detail-label'>Description</div><div>{html.escape(str(project['description']))}</div>
          <div class='detail-label'>Organization</div><div>{org_text}</div>
          <div class='detail-label'>Date Created</div><div>{project['date_created']}</div>
        </div>
      </div>
      <div class='header' style='padding-top:0;'><div><h2 class='title' style='font-size:1.1rem;'>Members</h2></div></div>
      {selector}
      <div class='table-wrap'><table><thead><tr><th>Name</th><th>Email</th></tr></thead><tbody>{member_rows}</tbody></table></div>
    """
    return HTMLResponse(page_shell("Project Detail", body))


@app.get("/organizations/{organization_id}", response_class=HTMLResponse)
def organization_detail(organization_id: int) -> HTMLResponse:
    ensure_schema()
    org = fetch_one("SELECT id, name, address, abn FROM organizations WHERE id = %s", (organization_id,))
    if not org:
        return HTMLResponse("Organization not found", status_code=404)

    projects = fetch_all(
        "SELECT id, name, description, date_created FROM projects WHERE organization_id = %s ORDER BY date_created DESC, id DESC",
        (organization_id,),
    )
    projects_rows = "".join(
        f"<tr><td><a href='/projects/{p['id']}'>{html.escape(str(p['name']))}</a></td><td>{html.escape(str(p['description']))}</td><td>{p['date_created']}</td></tr>"
        for p in projects
    ) or "<tr><td colspan='3' class='empty-row'>No projects assigned.</td></tr>"

    org_members = fetch_all(
        """
        SELECT m.id, m.first_name, m.middle_name, m.last_name, m.email
        FROM organization_members om JOIN members m ON m.id = om.member_id
        WHERE om.organization_id = %s ORDER BY m.first_name, m.last_name
        """,
        (organization_id,),
    )
    available_members = fetch_all(
        """
        SELECT m.id, m.first_name, m.middle_name, m.last_name
        FROM members m
        WHERE m.id NOT IN (SELECT member_id FROM organization_members WHERE organization_id = %s)
        ORDER BY m.first_name, m.last_name
        """,
        (organization_id,),
    )
    member_rows = "".join(
        f"<tr><td><a href='/members/{m['id']}'>{html.escape(m['first_name'])} {html.escape(m['middle_name'] or '')} {html.escape(m['last_name'])}</a></td><td>{html.escape(m['email'])}</td></tr>"
        for m in org_members
    ) or "<tr><td colspan='2' class='empty-row'>No members associated.</td></tr>"
    member_options = "".join(
        f"<option value='{m['id']}'>{html.escape(m['first_name'])} {html.escape(m['middle_name'] or '')} {html.escape(m['last_name'])}</option>"
        for m in available_members
    )
    member_selector = f"""
      <form method='post' action='/organizations/{organization_id}/members' style='margin:0 24px 18px;'>
        <div class='field'><label>Add Member to Organization</label><select name='member_id' required><option value=''>Choose member</option>{member_options}</select></div>
        <button class='btn-primary' type='submit'>Add Member</button>
      </form>
    """ if available_members else "<div style='padding:0 24px 14px; color:#6b7280;'>All members are already associated or no members exist.</div>"

    body = f"""
      <div class='header'><div><h1 class='title'>Organization: {html.escape(str(org['name']))}</h1><div class='subtitle'>Organization detail</div></div></div>
      <div class='details'>
        <div class='detail-grid'>
          <div class='detail-label'>Name</div><div>{html.escape(str(org['name']))}</div>
          <div class='detail-label'>Address</div><div>{html.escape(str(org['address'] or ''))}</div>
          <div class='detail-label'>ABN</div><div>{html.escape(str(org['abn'] or ''))}</div>
        </div>
      </div>
      <div class='header' style='padding-top:0;'><div><h2 class='title' style='font-size:1.1rem;'>Create Project in this Organization</h2></div></div>
      <form method='post' action='/organizations/{organization_id}/projects' style='padding:0 24px 14px;'>
        <div class='field'><label>Name</label><input name='name' maxlength='255' required /></div>
        <div class='field'><label>Description</label><textarea name='description' required></textarea></div>
        <div class='field'><label>Date Created</label><input name='date_created' type='date' value='{date.today().isoformat()}' required /></div>
        <button class='btn-primary' type='submit'>Create Project</button>
      </form>
      <div class='table-wrap'>
        <h2 style='margin:0 0 8px;'>Projects</h2>
        <table><thead><tr><th>Name</th><th>Description</th><th>Date Created</th></tr></thead><tbody>{projects_rows}</tbody></table>
      </div>
      <div class='header' style='padding-top:0;'><div><h2 class='title' style='font-size:1.1rem;'>Members</h2></div></div>
      {member_selector}
      <div class='table-wrap'>
        <table><thead><tr><th>Name</th><th>Email</th></tr></thead><tbody>{member_rows}</tbody></table>
      </div>
    """
    return HTMLResponse(page_shell("Organization Detail", body))


@app.get("/members/{member_id}", response_class=HTMLResponse)
def member_detail(member_id: int) -> HTMLResponse:
    ensure_schema()
    member = fetch_one("SELECT id, first_name, middle_name, last_name, phone, email FROM members WHERE id = %s", (member_id,))
    if not member:
        return HTMLResponse("Member not found", status_code=404)

    projects = fetch_all(
        """
        SELECT p.id, p.name, p.description, p.date_created
        FROM project_members pm JOIN projects p ON p.id = pm.project_id
        WHERE pm.member_id = %s ORDER BY p.date_created DESC, p.id DESC
        """,
        (member_id,),
    )
    organizations = fetch_all(
        """
        SELECT o.id, o.name, o.address, o.abn
        FROM organization_members om JOIN organizations o ON o.id = om.organization_id
        WHERE om.member_id = %s ORDER BY o.name
        """,
        (member_id,),
    )
    project_rows = "".join(
        f"<tr><td><a href='/projects/{p['id']}'>{html.escape(p['name'])}</a></td><td>{html.escape(p['description'])}</td><td>{p['date_created']}</td></tr>"
        for p in projects
    ) or "<tr><td colspan='3' class='empty-row'>This member is not assigned to any projects.</td></tr>"
    org_rows = "".join(
        f"<tr><td><a href='/organizations/{o['id']}'>{html.escape(str(o['name']))}</a></td><td>{html.escape(str(o['address'] or ''))}</td><td>{html.escape(str(o['abn'] or ''))}</td></tr>"
        for o in organizations
    ) or "<tr><td colspan='3' class='empty-row'>This member is not associated with any organizations.</td></tr>"

    body = f"""
      <div class='header'><div><h1 class='title'>Member: {html.escape(member['first_name'])} {html.escape(member['middle_name'] or '')} {html.escape(member['last_name'])}</h1><div class='subtitle'>Member detail</div></div></div>
      <div class='details'>
        <div class='detail-grid'>
          <div class='detail-label'>First-name</div><div>{html.escape(member['first_name'])}</div>
          <div class='detail-label'>Middle-name</div><div>{html.escape(member['middle_name'] or '')}</div>
          <div class='detail-label'>Last-name</div><div>{html.escape(member['last_name'])}</div>
          <div class='detail-label'>Phone</div><div>{html.escape(member['phone'] or '')}</div>
          <div class='detail-label'>Email</div><div>{html.escape(member['email'])}</div>
        </div>
      </div>
      <div class='table-wrap'>
        <h2 style='margin:0 0 8px;'>Projects</h2>
        <table><thead><tr><th>Name</th><th>Description</th><th>Date Created</th></tr></thead><tbody>{project_rows}</tbody></table>
      </div>
      <div class='table-wrap'>
        <h2 style='margin:0 0 8px;'>Organizations</h2>
        <table><thead><tr><th>Name</th><th>Address</th><th>ABN</th></tr></thead><tbody>{org_rows}</tbody></table>
      </div>
    """
    return HTMLResponse(page_shell("Member Detail", body))


@app.post("/projects")
def create_project(
    name: str = Form(...),
    description: str = Form(...),
    date_created: date = Form(...),
    organization_id: str = Form(""),
) -> RedirectResponse:
    ensure_schema()
    org_id = int(organization_id) if organization_id.strip() else None
    execute(
        "INSERT INTO projects (name, description, date_created, organization_id) VALUES (%s, %s, %s, %s)",
        (name.strip(), description.strip(), date_created, org_id),
    )
    return RedirectResponse(url="/projects", status_code=303)


@app.post("/projects/delete")
def delete_projects(project_ids: list[int] = Form(default=[])) -> RedirectResponse:
    ensure_schema()
    if project_ids:
        placeholders = ",".join(["%s"] * len(project_ids))
        execute_many(f"DELETE FROM projects WHERE id IN ({placeholders})", project_ids)
    return RedirectResponse(url="/projects", status_code=303)


@app.post("/organizations")
def create_organization(name: str = Form(...), address: str = Form(""), abn: str = Form("")) -> RedirectResponse:
    ensure_schema()
    execute(
        "INSERT INTO organizations (name, address, abn) VALUES (%s, %s, %s)",
        (name.strip(), address.strip() or None, abn.strip() or None),
    )
    return RedirectResponse(url="/organizations", status_code=303)


@app.post("/organizations/delete")
def delete_organizations(organization_ids: list[int] = Form(default=[])) -> RedirectResponse:
    ensure_schema()
    if organization_ids:
        placeholders = ",".join(["%s"] * len(organization_ids))
        execute_many(f"DELETE FROM organizations WHERE id IN ({placeholders})", organization_ids)
    return RedirectResponse(url="/organizations", status_code=303)


@app.post("/organizations/{organization_id}/projects")
def create_project_for_organization(
    organization_id: int,
    name: str = Form(...),
    description: str = Form(...),
    date_created: date = Form(...),
) -> RedirectResponse:
    ensure_schema()
    execute(
        "INSERT INTO projects (name, description, date_created, organization_id) VALUES (%s, %s, %s, %s)",
        (name.strip(), description.strip(), date_created, organization_id),
    )
    return RedirectResponse(url=f"/organizations/{organization_id}", status_code=303)


@app.post("/organizations/{organization_id}/members")
def add_member_to_organization(organization_id: int, member_id: int = Form(...)) -> RedirectResponse:
    ensure_schema()
    execute(
        "INSERT IGNORE INTO organization_members (organization_id, member_id) VALUES (%s, %s)",
        (organization_id, member_id),
    )
    return RedirectResponse(url=f"/organizations/{organization_id}", status_code=303)


@app.post("/members")
def create_member(
    first_name: str = Form(...),
    middle_name: str = Form(""),
    last_name: str = Form(...),
    phone: str = Form(""),
    email: str = Form(...),
) -> RedirectResponse:
    ensure_schema()
    execute(
        "INSERT INTO members (first_name, middle_name, last_name, phone, email) VALUES (%s, %s, %s, %s, %s)",
        (first_name.strip(), middle_name.strip() or None, last_name.strip(), phone.strip() or None, email.strip()),
    )
    return RedirectResponse(url="/members", status_code=303)


@app.post("/members/delete")
def delete_members(member_ids: list[int] = Form(default=[])) -> RedirectResponse:
    ensure_schema()
    if member_ids:
        placeholders = ",".join(["%s"] * len(member_ids))
        execute_many(f"DELETE FROM members WHERE id IN ({placeholders})", member_ids)
    return RedirectResponse(url="/members", status_code=303)


@app.post("/projects/{project_id}/members")
def add_member_to_project(project_id: int, member_id: int = Form(...)) -> RedirectResponse:
    ensure_schema()
    execute(
        "INSERT IGNORE INTO project_members (project_id, member_id) VALUES (%s, %s)",
        (project_id, member_id),
    )
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@app.get("/health", response_class=HTMLResponse)
def health() -> HTMLResponse:
    return HTMLResponse("ok")
