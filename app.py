import os
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import Column, Date, ForeignKey, Integer, String, Table, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

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


organization_members = Table(
    "organization_members",
    Base.metadata,
    Column("organization_id", ForeignKey("organizations.id"), primary_key=True),
    Column("member_id", ForeignKey("members.id"), primary_key=True),
)

project_members = Table(
    "project_members",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id"), primary_key=True),
    Column("member_id", ForeignKey("members.id"), primary_key=True),
)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    abn: Mapped[str | None] = mapped_column(String(64), nullable=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="organization")
    members: Mapped[list["Member"]] = relationship(
        secondary=organization_members,
        back_populates="organizations",
    )


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    organizations: Mapped[list[Organization]] = relationship(
        secondary=organization_members,
        back_populates="members",
    )
    projects: Mapped[list["Project"]] = relationship(
        secondary=project_members,
        back_populates="members",
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    date_created: Mapped[date] = mapped_column(Date, nullable=False)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)

    organization: Mapped[Organization | None] = relationship(back_populates="projects")
    members: Mapped[list[Member]] = relationship(
        secondary=project_members,
        back_populates="projects",
    )


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    abn: str | None = Field(default=None, max_length=64)


class OrganizationOut(BaseModel):
    id: int
    name: str
    address: str | None
    abn: str | None


class MemberCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    email: str = Field(min_length=1, max_length=255)
    organization_ids: list[int] = Field(default_factory=list)


class MemberOut(BaseModel):
    id: int
    first_name: str
    middle_name: str | None
    last_name: str
    phone: str | None
    email: str
    organization_ids: list[int]
    organization_names: list[str]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    date_created: date = Field(default_factory=date.today)
    organization_id: int | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    date_created: date
    organization_id: int | None
    organization_name: str | None


class ProjectMemberAdd(BaseModel):
    member_id: int


app = FastAPI(title="Codex Activity App")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def read_static_html(filename: str) -> str:
    return (STATIC_DIR / filename).read_text(encoding="utf-8")


def to_project_out(project: Project) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        date_created=project.date_created,
        organization_id=project.organization_id,
        organization_name=project.organization.name if project.organization else None,
    )


def to_member_out(member: Member) -> MemberOut:
    return MemberOut(
        id=member.id,
        first_name=member.first_name,
        middle_name=member.middle_name,
        last_name=member.last_name,
        phone=member.phone,
        email=member.email,
        organization_ids=[o.id for o in member.organizations],
        organization_names=[o.name for o in member.organizations],
    )


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return read_static_html("home.html")


@app.get("/projects", response_class=HTMLResponse)
def projects_page() -> str:
    return read_static_html("projects.html")


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail_page(project_id: int) -> str:
    return read_static_html("project_detail.html")


@app.get("/organizations", response_class=HTMLResponse)
def organizations_page() -> str:
    return read_static_html("organizations.html")


@app.get("/organizations/{organization_id}", response_class=HTMLResponse)
def organization_detail_page(organization_id: int) -> str:
    return read_static_html("organization_detail.html")


@app.get("/members", response_class=HTMLResponse)
def members_page() -> str:
    return read_static_html("members.html")


@app.get("/members/{member_id}", response_class=HTMLResponse)
def member_detail_page(member_id: int) -> str:
    return read_static_html("member_detail.html")


@app.get("/api/organizations", response_model=list[OrganizationOut])
def list_organizations(db: Session = Depends(get_db)) -> list[OrganizationOut]:
    rows = db.query(Organization).order_by(Organization.id.asc()).all()
    return [OrganizationOut(id=o.id, name=o.name, address=o.address, abn=o.abn) for o in rows]


@app.post("/api/organizations", response_model=OrganizationOut)
def create_organization(payload: OrganizationCreate, db: Session = Depends(get_db)) -> OrganizationOut:
    org = Organization(
        name=payload.name.strip(),
        address=(payload.address or "").strip() or None,
        abn=(payload.abn or "").strip() or None,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return OrganizationOut(id=org.id, name=org.name, address=org.address, abn=org.abn)


@app.get("/api/organizations/{organization_id}", response_model=OrganizationOut)
def get_organization(organization_id: int, db: Session = Depends(get_db)) -> OrganizationOut:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationOut(id=org.id, name=org.name, address=org.address, abn=org.abn)


@app.delete("/api/organizations/{organization_id}")
def delete_organization(organization_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    for project in org.projects:
        project.organization_id = None

    db.delete(org)
    db.commit()
    return {"status": "deleted"}


@app.get("/api/members", response_model=list[MemberOut])
def list_members(db: Session = Depends(get_db)) -> list[MemberOut]:
    rows = db.query(Member).order_by(Member.id.asc()).all()
    return [to_member_out(m) for m in rows]


@app.post("/api/members", response_model=MemberOut)
def create_member(payload: MemberCreate, db: Session = Depends(get_db)) -> MemberOut:
    member = Member(
        first_name=payload.first_name.strip(),
        middle_name=(payload.middle_name or "").strip() or None,
        last_name=payload.last_name.strip(),
        phone=(payload.phone or "").strip() or None,
        email=payload.email.strip(),
    )

    if payload.organization_ids:
        orgs = db.query(Organization).filter(Organization.id.in_(payload.organization_ids)).all()
        member.organizations = orgs

    db.add(member)
    db.commit()
    db.refresh(member)
    return to_member_out(member)


@app.get("/api/members/{member_id}", response_model=MemberOut)
def get_member(member_id: int, db: Session = Depends(get_db)) -> MemberOut:
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return to_member_out(member)


@app.delete("/api/members/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()
    return {"status": "deleted"}


@app.get("/api/members/{member_id}/projects", response_model=list[ProjectOut])
def list_projects_for_member(member_id: int, db: Session = Depends(get_db)) -> list[ProjectOut]:
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return [to_project_out(project) for project in member.projects]


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectOut]:
    projects = db.query(Project).order_by(Project.id.asc()).all()
    return [to_project_out(project) for project in projects]


@app.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)) -> ProjectOut:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return to_project_out(project)


@app.get("/api/organizations/{organization_id}/projects", response_model=list[ProjectOut])
def list_projects_for_organization(organization_id: int, db: Session = Depends(get_db)) -> list[ProjectOut]:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    projects = db.query(Project).filter(Project.organization_id == organization_id).order_by(Project.id.asc()).all()
    return [to_project_out(project) for project in projects]


@app.post("/api/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectOut:
    if payload.organization_id is not None:
        org = db.query(Organization).filter(Organization.id == payload.organization_id).first()
        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found")

    project = Project(
        name=payload.name.strip(),
        description=payload.description.strip(),
        date_created=payload.date_created,
        organization_id=payload.organization_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return to_project_out(project)


@app.post("/api/organizations/{organization_id}/projects", response_model=ProjectOut)
def create_project_for_organization(
    organization_id: int,
    payload: ProjectCreate,
    db: Session = Depends(get_db),
) -> ProjectOut:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    project = Project(
        name=payload.name.strip(),
        description=payload.description.strip(),
        date_created=payload.date_created,
        organization_id=organization_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return to_project_out(project)


@app.get("/api/projects/{project_id}/members", response_model=list[MemberOut])
def list_project_members(project_id: int, db: Session = Depends(get_db)) -> list[MemberOut]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return [to_member_out(member) for member in project.members]


@app.get("/api/projects/{project_id}/available-members", response_model=list[MemberOut])
def list_available_members_for_project(project_id: int, db: Session = Depends(get_db)) -> list[MemberOut]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    query = db.query(Member)
    if project.organization_id is not None:
        query = query.join(Member.organizations).filter(Organization.id == project.organization_id)

    existing_ids = {member.id for member in project.members}
    rows = query.distinct().order_by(Member.id.asc()).all()
    filtered = [member for member in rows if member.id not in existing_ids]
    return [to_member_out(m) for m in filtered]


@app.post("/api/projects/{project_id}/members", response_model=list[MemberOut])
def add_member_to_project(project_id: int, payload: ProjectMemberAdd, db: Session = Depends(get_db)) -> list[MemberOut]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    member = db.query(Member).filter(Member.id == payload.member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    if project.organization_id is not None:
        org_ids = {o.id for o in member.organizations}
        if project.organization_id not in org_ids:
            raise HTTPException(status_code=400, detail="Member is not part of the project's organization")

    if member not in project.members:
        project.members.append(member)
        db.commit()
        db.refresh(project)

    return [to_member_out(m) for m in project.members]


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"status": "deleted"}
