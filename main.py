import os
from datetime import date

import mysql.connector
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI(title="CodexActivityApp")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    date_created: date


def db_config() -> dict[str, str | int]:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "codex_app"),
        "password": os.getenv("DB_PASSWORD", "codex_password"),
        "database": os.getenv("DB_NAME", "codex_activity_app"),
    }


def get_connection() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(**db_config())


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"today": date.today().isoformat()},
    )


@app.get("/api/projects")
def list_projects():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, description, date_created FROM projects ORDER BY date_created DESC, id DESC"
        )
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as exc:
        return JSONResponse(status_code=500, content={"error": f"Database error: {exc.msg}"})
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals() and conn.is_connected():
            conn.close()


@app.post("/api/projects")
def create_project(payload: ProjectIn):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (name, description, date_created) VALUES (%s, %s, %s)",
            (payload.name, payload.description, payload.date_created),
        )
        conn.commit()
        return {"id": cursor.lastrowid}
    except mysql.connector.Error as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc.msg}") from exc
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals() and conn.is_connected():
            conn.close()


@app.put("/api/projects/{project_id}")
def update_project(project_id: int, payload: ProjectIn):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE projects SET name = %s, description = %s, date_created = %s WHERE id = %s",
            (payload.name, payload.description, payload.date_created, project_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"status": "ok"}
    except mysql.connector.Error as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc.msg}") from exc
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals() and conn.is_connected():
            conn.close()


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"status": "ok"}
    except mysql.connector.Error as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc.msg}") from exc
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals() and conn.is_connected():
            conn.close()
