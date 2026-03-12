import os
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import Column, Date, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _required_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


DB_HOST = _required_env("DB_HOST", "127.0.0.1")
DB_PORT = int(_required_env("DB_PORT", "3306"))
DB_NAME = _required_env("DB_NAME", "codex_activity_app")
DB_USER = _required_env("DB_USER", "codex_app_user")
DB_PASSWORD = _required_env("DB_PASSWORD", "codex_app_password")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False)
    date_created = Column(Date, nullable=False)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    date_created: date


app = FastAPI(title="CodexActivityApp")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    today = date.today().isoformat()
    return f"""
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Project Dashboard</title>
    <style>
      :root {{
        --bg: #f1f5f9;
        --card: #ffffff;
        --text: #0f172a;
        --muted: #64748b;
        --primary: #1d4ed8;
        --primary-dark: #1e40af;
        --danger: #dc2626;
        --danger-dark: #b91c1c;
        --border: #dbe2ea;
      }}

      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
      }}
      .container {{
        max-width: 1000px;
        margin: 48px auto;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        overflow: hidden;
      }}
      .header {{
        padding: 24px;
        border-bottom: 1px solid var(--border);
      }}
      .title {{ margin: 0; font-size: 1.6rem; font-weight: 700; }}
      .subtitle {{ margin: 6px 0 0; color: var(--muted); font-size: 0.95rem; }}
      .content {{ padding: 20px 24px 28px; }}
      .toolbar {{
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        margin-bottom: 14px;
      }}
      button {{
        border: 0;
        border-radius: 8px;
        padding: 10px 14px;
        font-weight: 600;
        cursor: pointer;
      }}
      .btn-add {{ background: var(--primary); color: white; }}
      .btn-add:hover {{ background: var(--primary-dark); }}
      .btn-delete {{ background: var(--danger); color: white; }}
      .btn-delete:hover {{ background: var(--danger-dark); }}
      .btn-cancel {{ background: #e2e8f0; color: #0f172a; }}

      table {{ width: 100%; border-collapse: collapse; }}
      thead th {{
        text-align: left;
        font-size: 0.85rem;
        color: var(--muted);
        letter-spacing: .02em;
        background: #f8fafc;
      }}
      th, td {{
        border: 1px solid var(--border);
        padding: 12px;
        vertical-align: top;
      }}
      tbody tr:hover {{ background: #f8fafc; }}
      .empty-row {{ text-align: center; color: var(--muted); }}

      dialog {{
        border: 0;
        border-radius: 12px;
        width: min(560px, 92vw);
        box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
      }}
      dialog::backdrop {{ background: rgba(15, 23, 42, 0.5); }}
      .dialog-body {{ padding: 20px; }}
      .dialog-title {{ margin-top: 0; margin-bottom: 14px; }}
      .field {{ margin-bottom: 12px; }}
      label {{ display: block; margin-bottom: 6px; font-weight: 600; }}
      input, textarea {{
        width: 100%;
        padding: 10px;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        font: inherit;
      }}
      textarea {{ min-height: 90px; resize: vertical; }}
      .dialog-actions {{ display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }}
      .status {{ margin-top: 10px; min-height: 1.2rem; color: var(--muted); font-size: 0.9rem; }}
    </style>
  </head>
  <body>
    <div class=\"container\">
      <div class=\"header\">
        <h1 class=\"title\">Project Portfolio</h1>
        <p class=\"subtitle\">Codex built this!</p>
      </div>
      <div class=\"content\">
        <div class=\"toolbar\">
          <button class=\"btn-add\" id=\"addBtn\">Add Project</button>
          <button class=\"btn-delete\" id=\"deleteBtn\">Delete Selected</button>
        </div>

        <table aria-label=\"Projects\">
          <thead>
            <tr>
              <th style=\"width:42px\"></th>
              <th>Name</th>
              <th>Description</th>
              <th style=\"width:170px\">Date Created</th>
            </tr>
          </thead>
          <tbody id=\"projectsTableBody\"></tbody>
        </table>
        <div class=\"status\" id=\"status\"></div>
      </div>
    </div>

    <dialog id=\"projectDialog\">
      <form class=\"dialog-body\" id=\"projectForm\">
        <h2 class=\"dialog-title\">Create Project</h2>

        <div class=\"field\">
          <label for=\"name\">Name</label>
          <input id=\"name\" name=\"name\" required maxlength=\"255\" />
        </div>

        <div class=\"field\">
          <label for=\"description\">Description</label>
          <textarea id=\"description\" name=\"description\" required maxlength=\"1000\"></textarea>
        </div>

        <div class=\"field\">
          <label for=\"date_created\">Date Created</label>
          <input id=\"date_created\" name=\"date_created\" type=\"date\" value=\"{today}\" required />
        </div>

        <div class=\"dialog-actions\">
          <button type=\"button\" class=\"btn-cancel\" id=\"cancelDialogBtn\">Cancel</button>
          <button type=\"submit\" class=\"btn-add\">Save Project</button>
        </div>
      </form>
    </dialog>

    <script>
      const addBtn = document.getElementById('addBtn');
      const deleteBtn = document.getElementById('deleteBtn');
      const dialog = document.getElementById('projectDialog');
      const cancelDialogBtn = document.getElementById('cancelDialogBtn');
      const form = document.getElementById('projectForm');
      const tableBody = document.getElementById('projectsTableBody');
      const statusEl = document.getElementById('status');

      let selectedProjectId = null;

      function setStatus(message, isError = false) {{
        statusEl.textContent = message;
        statusEl.style.color = isError ? '#b91c1c' : '#64748b';
      }}

      function escapeHtml(value) {{
        return value
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('"', '&quot;')
          .replaceAll("'", '&#039;');
      }}

      async function loadProjects() {{
        const response = await fetch('/api/projects');
        const projects = await response.json();

        if (!projects.length) {{
          tableBody.innerHTML = `
            <tr>
              <td colspan=\"4\" class=\"empty-row\">No projects yet. Click \"Add Project\" to create one.</td>
            </tr>
          `;
          selectedProjectId = null;
          return;
        }}

        tableBody.innerHTML = projects
          .map((project) => `
            <tr>
              <td>
                <input
                  type=\"radio\"
                  name=\"selected_project\"
                  value=\"${{project.id}}\"
                  ${{selectedProjectId === project.id ? 'checked' : ''}}
                />
              </td>
              <td>${{escapeHtml(project.name)}}</td>
              <td>${{escapeHtml(project.description)}}</td>
              <td>${{project.date_created}}</td>
            </tr>
          `)
          .join('');

        document.querySelectorAll('input[name="selected_project"]').forEach((input) => {{
          input.addEventListener('change', () => {{
            selectedProjectId = Number(input.value);
          }});
        }});
      }}

      addBtn.addEventListener('click', () => {{
        form.reset();
        document.getElementById('date_created').value = '{today}';
        dialog.showModal();
      }});

      cancelDialogBtn.addEventListener('click', () => dialog.close());

      form.addEventListener('submit', async (event) => {{
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(form).entries());

        const response = await fetch('/api/projects', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload),
        }});

        if (!response.ok) {{
          const err = await response.text();
          setStatus(`Could not create project: ${{err}}`, true);
          return;
        }}

        dialog.close();
        setStatus('Project created.');
        await loadProjects();
      }});

      deleteBtn.addEventListener('click', async () => {{
        if (!selectedProjectId) {{
          setStatus('Select a project to delete.', true);
          return;
        }}

        const confirmed = window.confirm('Delete the selected project?');
        if (!confirmed) return;

        const response = await fetch(`/api/projects/${{selectedProjectId}}`, {{ method: 'DELETE' }});
        if (!response.ok) {{
          setStatus('Could not delete project.', true);
          return;
        }}

        setStatus('Project deleted.');
        selectedProjectId = null;
        await loadProjects();
      }});

      loadProjects().catch((error) => {{
        setStatus(`Failed to load projects: ${{error}}`, true);
      }});
    </script>
  </body>
</html>
    """


@app.get("/api/projects")
def list_projects() -> list[dict]:
    with SessionLocal() as db:
        projects = db.query(Project).order_by(Project.date_created.desc(), Project.id.desc()).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "date_created": p.date_created.isoformat(),
            }
            for p in projects
        ]


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate) -> dict:
    with SessionLocal() as db:
        project = Project(
            name=payload.name.strip(),
            description=payload.description.strip(),
            date_created=payload.date_created,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "date_created": project.date_created.isoformat(),
        }


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: int) -> None:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        db.delete(project)
        db.commit()
