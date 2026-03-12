import os
from datetime import date

import pymysql
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Codex Projects")

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


def ensure_table() -> None:
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


@app.on_event("startup")
def startup() -> None:
    try:
        ensure_table()
    except Exception as exc:  # provide visible startup error in logs
        raise RuntimeError(f"Database initialization failed: {exc}") from exc


@app.get("/", response_class=HTMLResponse)
def read_root() -> str:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, description, date_created FROM projects ORDER BY date_created DESC, id DESC"
            )
            projects = cursor.fetchall()

    rows = "\n".join(
        f"""
        <tr>
          <td>{project['name']}</td>
          <td>{project['description']}</td>
          <td>{project['date_created']}</td>
          <td>
            <form method=\"post\" action=\"/projects/{project['id']}/delete\" onsubmit=\"return confirm('Delete this project?');\">
              <button class=\"danger small\" type=\"submit\">Delete</button>
            </form>
          </td>
        </tr>
        """
        for project in projects
    )

    empty_state = ""
    if not projects:
        empty_state = "<tr><td colspan='4' class='empty'>No projects yet. Click Add Project to create one.</td></tr>"

    today = date.today().isoformat()
    return f"""
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Projects Dashboard</title>
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
      .container {{
        max-width: 1020px;
        margin: 40px auto;
        padding: 0 20px;
      }}
      .card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(31, 42, 68, 0.06);
        overflow: hidden;
      }}
      .header {{
        padding: 24px;
        border-bottom: 1px solid var(--border);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }}
      h1 {{ margin: 0; font-size: 1.4rem; }}
      .subtitle {{ margin: 4px 0 0; color: var(--muted); font-size: 0.95rem; }}
      .actions {{ display: flex; gap: 10px; }}
      button {{
        border: 0;
        border-radius: 10px;
        padding: 10px 16px;
        font-weight: 600;
        cursor: pointer;
      }}
      .primary {{ background: var(--primary); color: white; }}
      .primary:hover {{ background: var(--primary-dark); }}
      .danger {{ background: var(--danger); color: white; }}
      .danger:hover {{ background: var(--danger-dark); }}
      .small {{ padding: 6px 10px; font-size: 0.82rem; }}
      table {{ width: 100%; border-collapse: collapse; }}
      thead th {{
        text-align: left;
        background: #eef3ff;
        color: #35507a;
        padding: 14px;
        font-size: 0.88rem;
        letter-spacing: 0.02em;
        text-transform: uppercase;
      }}
      tbody td {{ padding: 14px; border-top: 1px solid var(--border); vertical-align: top; }}
      .empty {{ text-align: center; color: var(--muted); padding: 30px; }}
      dialog {{
        border: 1px solid var(--border);
        border-radius: 12px;
        width: 460px;
        max-width: 92vw;
      }}
      dialog::backdrop {{ background: rgba(9, 20, 40, 0.45); }}
      .dialog-title {{ margin-top: 0; }}
      .field {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }}
      .field input, .field textarea {{
        border: 1px solid #b7c6dd;
        border-radius: 8px;
        padding: 10px;
        font: inherit;
      }}
      .dialog-actions {{ display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }}
      .secondary {{ background: #e6eaf4; color: #2e405f; }}
    </style>
  </head>
  <body>
    <div class=\"container\">
      <div class=\"card\">
        <div class=\"header\">
          <div>
            <h1>Projects</h1>
            <p class=\"subtitle\">Codex built this!</p>
          </div>
          <div class=\"actions\">
            <button class=\"primary\" onclick=\"document.getElementById('addProjectDialog').showModal()\">Add Project</button>
            <button class=\"danger\" onclick=\"document.getElementById('deleteAllDialog').showModal()\">Delete All</button>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>Date Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows}
            {empty_state}
          </tbody>
        </table>
      </div>
    </div>

    <dialog id=\"addProjectDialog\">
      <form method=\"post\" action=\"/projects\">
        <h3 class=\"dialog-title\">Create Project</h3>
        <div class=\"field\">
          <label for=\"name\">Name</label>
          <input id=\"name\" name=\"name\" required maxlength=\"255\" />
        </div>
        <div class=\"field\">
          <label for=\"description\">Description</label>
          <textarea id=\"description\" name=\"description\" required rows=\"4\"></textarea>
        </div>
        <div class=\"field\">
          <label for=\"date_created\">Date Created</label>
          <input id=\"date_created\" name=\"date_created\" type=\"date\" value=\"{today}\" required />
        </div>
        <div class=\"dialog-actions\">
          <button type=\"button\" class=\"secondary\" onclick=\"document.getElementById('addProjectDialog').close()\">Cancel</button>
          <button type=\"submit\" class=\"primary\">Create</button>
        </div>
      </form>
    </dialog>

    <dialog id=\"deleteAllDialog\">
      <form method=\"post\" action=\"/projects/delete-all\" onsubmit=\"return confirm('Delete ALL projects?');\">
        <h3 class=\"dialog-title\">Delete All Projects</h3>
        <p>This removes all rows from the projects table.</p>
        <div class=\"dialog-actions\">
          <button type=\"button\" class=\"secondary\" onclick=\"document.getElementById('deleteAllDialog').close()\">Cancel</button>
          <button type=\"submit\" class=\"danger\">Delete All</button>
        </div>
      </form>
    </dialog>
  </body>
</html>
"""


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
    return RedirectResponse(url="/", status_code=303)


@app.post("/projects/{project_id}/delete")
def delete_project(project_id: int) -> RedirectResponse:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Project not found")
    return RedirectResponse(url="/", status_code=303)


@app.post("/projects/delete-all")
def delete_all_projects() -> RedirectResponse:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM projects")
    return RedirectResponse(url="/", status_code=303)
