from __future__ import annotations

import os
from datetime import date, datetime

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Date, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    date_created: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)


DB_USER = os.getenv("APP_DB_USER", "codex_app")
DB_PASSWORD = os.getenv("APP_DB_PASSWORD", "codex_password")
DB_HOST = os.getenv("APP_DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("APP_DB_PORT", "3306")
DB_NAME = os.getenv("APP_DB_NAME", "codex_activity_app")

DEFAULT_DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)
DATABASE_URL = os.getenv("APP_DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base.metadata.create_all(engine)

app = FastAPI(title="Codex Activity App")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def read_index(request: Request) -> HTMLResponse:
    with Session(engine) as session:
        projects = session.scalars(select(Project).order_by(Project.date_created.desc(), Project.id.desc())).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"projects": projects},
    )


@app.post("/projects")
def create_project(name: str = Form(...), description: str = Form(...), date_created: str = Form(...)):
    name = name.strip()
    description = description.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")
    if not description:
        raise HTTPException(status_code=400, detail="Project description is required")

    try:
        parsed_date = datetime.strptime(date_created, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format") from exc

    with Session(engine) as session:
        session.add(Project(name=name, description=description, date_created=parsed_date))
        session.commit()

    return RedirectResponse(url="/", status_code=303)


@app.post("/projects/delete")
def delete_projects(project_ids: list[int] = Form(default=[])) -> JSONResponse:
    if not project_ids:
        raise HTTPException(status_code=400, detail="No projects selected")

    with Session(engine) as session:
        projects = session.scalars(select(Project).where(Project.id.in_(project_ids))).all()
        for project in projects:
            session.delete(project)
        session.commit()

    return JSONResponse({"deleted": len(projects)})
