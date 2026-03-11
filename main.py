import os
from datetime import date
from typing import Any

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import mysql.connector
from mysql.connector import Error

app = FastAPI(title="Codex Activity App")


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
        CREATE TABLE IF NOT EXISTS projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            date_created DATE NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    conn.commit()
    cursor.close()
    conn.close()


def fetch_projects() -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, name, description, date_created
        FROM projects
        ORDER BY date_created DESC, id DESC
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def render_page(projects: list[dict[str, Any]], error_message: str | None = None) -> str:
    rows = "\n".join(
        f"""
        <tr>
          <td><input type='checkbox' name='project_ids' value='{project['id']}' /></td>
          <td>{project['name']}</td>
          <td>{project['description']}</td>
          <td>{project['date_created']}</td>
        </tr>
        """
        for project in projects
    )

    if not rows:
        rows = """
        <tr>
          <td colspan='4' class='empty-row'>No projects found. Click “Add Project” to create one.</td>
        </tr>
        """

    error_html = f"<div class='error'>{error_message}</div>" if error_message else ""

    return f"""
<!doctype html>
<html lang='en'>
  <head>
    <meta charset='UTF-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1.0' />
    <title>Project Portfolio</title>
    <style>
      :root {{
        --bg: #f3f6fb;
        --panel: #ffffff;
        --text: #1f2937;
        --muted: #6b7280;
        --line: #e5e7eb;
        --primary: #1f6feb;
        --primary-dark: #1557bf;
        --danger: #b42318;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
      }}
      .container {{
        max-width: 1100px;
        margin: 48px auto;
        padding: 0 24px;
      }}
      .card {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 14px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        overflow: hidden;
      }}
      .header {{
        padding: 24px;
        border-bottom: 1px solid var(--line);
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 16px;
      }}
      .title {{ margin: 0; font-size: 1.5rem; }}
      .subtitle {{ margin-top: 6px; color: var(--muted); }}
      .actions {{ display: flex; gap: 10px; }}
      button {{
        border: none;
        border-radius: 8px;
        padding: 10px 16px;
        font-weight: 600;
        cursor: pointer;
      }}
      .btn-primary {{ background: var(--primary); color: white; }}
      .btn-primary:hover {{ background: var(--primary-dark); }}
      .btn-danger {{ background: var(--danger); color: white; }}
      .btn-danger:hover {{ filter: brightness(0.95); }}
      .table-wrap {{ padding: 0 24px 24px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
      th, td {{ padding: 12px 10px; text-align: left; border-bottom: 1px solid var(--line); }}
      th {{ color: var(--muted); font-size: 0.83rem; text-transform: uppercase; letter-spacing: 0.03em; }}
      .empty-row {{ text-align: center; color: var(--muted); padding: 26px 10px; }}
      .error {{ margin: 16px 24px 0; padding: 12px 14px; background: #fef3f2; color: #7a271a; border: 1px solid #fecdca; border-radius: 8px; }}
      dialog {{ border: none; border-radius: 12px; padding: 0; width: min(520px, 96%); }}
      dialog::backdrop {{ background: rgba(15, 23, 42, 0.45); }}
      .dialog-body {{ padding: 20px; }}
      .field {{ display: flex; flex-direction: column; margin-bottom: 14px; }}
      label {{ margin-bottom: 6px; color: #374151; font-weight: 600; }}
      input, textarea {{ border: 1px solid #d0d7de; border-radius: 8px; padding: 10px; font-size: 0.95rem; }}
      textarea {{ min-height: 96px; resize: vertical; }}
      .dialog-actions {{ display: flex; justify-content: flex-end; gap: 10px; margin-top: 4px; }}
      .btn-secondary {{ background: #eef2f7; color: #344054; }}
    </style>
  </head>
  <body>
    <div class='container'>
      <div class='card'>
        <div class='header'>
          <div>
            <h1 class='title'>Project Portfolio</h1>
            <div class='subtitle'>Codex built this!</div>
          </div>
          <div class='actions'>
            <button class='btn-primary' type='button' onclick='openDialog()'>Add Project</button>
            <button class='btn-danger' type='submit' form='deleteForm'>Delete Selected</button>
          </div>
        </div>
        {error_html}
        <div class='table-wrap'>
          <form id='deleteForm' method='post' action='/projects/delete'>
            <table>
              <thead>
                <tr>
                  <th style='width:48px;'>Select</th>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Date Created</th>
                </tr>
              </thead>
              <tbody>
                {rows}
              </tbody>
            </table>
          </form>
        </div>
      </div>
    </div>

    <dialog id='createDialog'>
      <form method='post' action='/projects'>
        <div class='dialog-body'>
          <h2>Create New Project</h2>
          <div class='field'>
            <label for='name'>Name</label>
            <input id='name' name='name' maxlength='255' required />
          </div>
          <div class='field'>
            <label for='description'>Description</label>
            <textarea id='description' name='description' required></textarea>
          </div>
          <div class='field'>
            <label for='date_created'>Date Created</label>
            <input id='date_created' name='date_created' type='date' value='{date.today().isoformat()}' required />
          </div>
          <div class='dialog-actions'>
            <button type='button' class='btn-secondary' onclick='closeDialog()'>Cancel</button>
            <button type='submit' class='btn-primary'>Save Project</button>
          </div>
        </div>
      </form>
    </dialog>

    <script>
      const dialog = document.getElementById('createDialog');
      function openDialog() {{ dialog.showModal(); }}
      function closeDialog() {{ dialog.close(); }}
    </script>
  </body>
</html>
    """


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    try:
        ensure_schema()
        projects = fetch_projects()
        return HTMLResponse(render_page(projects))
    except Error as exc:
        return HTMLResponse(render_page([], f"Database error: {exc}"), status_code=500)


@app.post("/projects")
def create_project(name: str = Form(...), description: str = Form(...), date_created: date = Form(...)) -> RedirectResponse:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (name, description, date_created) VALUES (%s, %s, %s)",
        (name.strip(), description.strip(), date_created),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return RedirectResponse(url="/", status_code=303)


@app.post("/projects/delete")
def delete_projects(project_ids: list[int] = Form(default=[])) -> RedirectResponse:
    if project_ids:
        conn = get_connection()
        cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(project_ids))
        cursor.execute(f"DELETE FROM projects WHERE id IN ({placeholders})", project_ids)
        conn.commit()
        cursor.close()
        conn.close()
    return RedirectResponse(url="/", status_code=303)
