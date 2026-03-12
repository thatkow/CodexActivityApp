import os
from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import Date, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DB_USER = os.getenv("DB_USER", "codex_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "codex_password")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "codex_activity")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    date_created: Mapped[date] = mapped_column(Date, nullable=False)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    date_created: date = Field(default_factory=date.today)


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    date_created: date


app = FastAPI(title="Codex Activity App")
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def read_root() -> str:
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectOut]:
    return db.query(Project).order_by(Project.id.asc()).all()


@app.post("/api/projects", response_model=ProjectOut)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)) -> ProjectOut:
    new_project = Project(
        name=project.name.strip(),
        description=project.description.strip(),
        date_created=project.date_created,
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"status": "deleted"}
