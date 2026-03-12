import os
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, Date, ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


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
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

COMMON_CSS = """
body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#eef2f7;color:#0f172a}
.container{max-width:1100px;margin:28px auto;background:#fff;border:1px solid #dbe2ea;border-radius:12px;padding:22px;box-shadow:0 10px 30px rgba(15,23,42,.08)}
.topnav{display:flex;gap:12px;margin-bottom:12px}.topnav a{text-decoration:none;color:#1d4ed8;font-weight:600}
h1{margin:8px 0 18px}.toolbar{display:flex;justify-content:flex-end;gap:10px;margin-bottom:12px;align-items:center}
button{border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}.primary{background:#1d4ed8;color:#fff}.danger{background:#dc2626;color:#fff}
table{width:100%;border-collapse:collapse}th,td{border:1px solid #dbe2ea;padding:10px;vertical-align:top}thead th{text-align:left;background:#f8fafc;color:#64748b}
a{color:#1d4ed8}
.status{min-height:1.1rem;color:#64748b}.status.err{color:#b91c1c}
.muted{text-align:center;color:#64748b}
.form{display:grid;gap:10px}.form label{display:grid;gap:6px;font-weight:600}.form input,.form textarea,.form select,select{padding:9px;border:1px solid #cbd5e1;border-radius:8px}
.actions{display:flex;justify-content:flex-end;gap:8px;margin-top:6px}
.card{background:#f8fafc;border:1px solid #dbe2ea;border-radius:10px;padding:14px;margin-bottom:16px}
dialog{border:0;border-radius:12px;box-shadow:0 20px 50px rgba(15,23,42,.25);width:min(600px,92vw)}
"""


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "member_id", name="uq_project_member"),)

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False)
    date_created = Column(Date, nullable=False)

    members = relationship("Member", secondary="project_members", back_populates="projects")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(120), nullable=False)
    middle_name = Column(String(120), nullable=True)
    last_name = Column(String(120), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=False, unique=True)

    projects = relationship("Project", secondary="project_members", back_populates="members")


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    date_created: date


class MemberCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    middle_name: Optional[str] = Field(default=None, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: EmailStr


class ProjectMemberLink(BaseModel):
    member_id: int


app = FastAPI(title="CodexActivityApp")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Home</title>
<style>body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#eef2f7;color:#0f172a;display:grid;place-items:center;min-height:100vh}.wrap{width:min(900px,92vw)}.title{margin:0;font-size:2rem}.sub{margin:8px 0 20px;color:#64748b}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}.tile{display:block;text-decoration:none;background:#fff;padding:24px;border:1px solid #dbe2ea;border-radius:14px;box-shadow:0 10px 26px rgba(15,23,42,.08)}.tile h2{margin:0 0 8px;color:#1d4ed8}.tile p{margin:0;color:#475569}</style></head>
<body><div class="wrap"><h1 class="title">Business Workspace</h1><p class="sub">Codex built this!</p><div class="tiles"><a class="tile" href="/projects"><h2>Projects</h2><p>Manage projects and assignments.</p></a><a class="tile" href="/members"><h2>Members</h2><p>Manage members and project memberships.</p></a></div></div></body></html>
"""


@app.get("/projects", response_class=HTMLResponse)
def projects_page() -> str:
    html = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Projects</title><style>__CSS__</style></head>
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/members">Members</a></div>
<h1>Projects</h1>
<div class="toolbar"><button class="primary" id="addBtn">Add Project</button><button class="danger" id="delBtn">Delete Selected</button></div>
<table><thead><tr><th></th><th>Name</th><th>Description</th><th>Date Created</th></tr></thead><tbody id="rows"></tbody></table><p id="status" class="status"></p>
</div>
<dialog id="dlg"><form id="frm" class="form"><h2>Add Project</h2>
<label>Name<input name="name" required maxlength="255"/></label>
<label>Description<textarea name="description" required maxlength="1000"></textarea></label>
<label>Date Created<input type="date" name="date_created" value="__TODAY__" required/></label>
<div class="actions"><button type="button" id="cancel">Cancel</button><button class="primary" type="submit">Save</button></div>
</form></dialog>
<script>
const rows=document.getElementById('rows'),status=document.getElementById('status');let selected=null;
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function load(){const r=await fetch('/api/projects');const data=await r.json();if(!data.length){rows.innerHTML='<tr><td colspan="4" class="muted">No projects yet.</td></tr>';return;}
rows.innerHTML=data.map(p=>`<tr><td><input type="radio" name="sel" value="${p.id}" ${selected===p.id?'checked':''}></td><td><a href="/projects/${p.id}">${esc(p.name)}</a></td><td>${esc(p.description)}</td><td>${p.date_created}</td></tr>`).join('');
document.querySelectorAll('input[name="sel"]').forEach(i=>i.onchange=()=>selected=Number(i.value));}
addBtn.onclick=()=>dlg.showModal();cancel.onclick=()=>dlg.close();
frm.onsubmit=async(e)=>{e.preventDefault();const payload=Object.fromEntries(new FormData(frm).entries());const r=await fetch('/api/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok){status.textContent='Create failed';status.className='status err';return;}dlg.close();status.textContent='Project created';status.className='status';load();};
delBtn.onclick=async()=>{if(!selected){status.textContent='Select a project first';status.className='status err';return;}const r=await fetch('/api/projects/'+selected,{method:'DELETE'});if(!r.ok){status.textContent='Delete failed';status.className='status err';return;}selected=null;status.textContent='Deleted';status.className='status';load();};
load();
</script></body></html>
"""
    return html.replace("__CSS__", COMMON_CSS).replace("__TODAY__", date.today().isoformat())


@app.get("/members", response_class=HTMLResponse)
def members_page() -> str:
    html = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Members</title><style>__CSS__</style></head>
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/projects">Projects</a></div>
<h1>Members</h1>
<div class="toolbar"><button class="primary" id="addBtn">Add Member</button><button class="danger" id="delBtn">Delete Selected</button></div>
<table><thead><tr><th></th><th>First-name</th><th>Middle-name</th><th>Last-name</th><th>Phone</th><th>Email</th></tr></thead><tbody id="rows"></tbody></table><p id="status" class="status"></p>
</div>
<dialog id="dlg"><form id="frm" class="form"><h2>Add Member</h2>
<label>First-name<input name="first_name" required maxlength="120"/></label>
<label>Middle-name (optional)<input name="middle_name" maxlength="120"/></label>
<label>Last-name<input name="last_name" required maxlength="120"/></label>
<label>Phone (optional)<input name="phone" maxlength="50"/></label>
<label>Email<input type="email" name="email" required maxlength="255"/></label>
<div class="actions"><button type="button" id="cancel">Cancel</button><button class="primary" type="submit">Save</button></div>
</form></dialog>
<script>
const rows=document.getElementById('rows'),status=document.getElementById('status');let selected=null;
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function load(){const r=await fetch('/api/members');const data=await r.json();if(!data.length){rows.innerHTML='<tr><td colspan="6" class="muted">No members yet.</td></tr>';return;}
rows.innerHTML=data.map(m=>`<tr><td><input type="radio" name="sel" value="${m.id}" ${selected===m.id?'checked':''}></td><td><a href="/members/${m.id}">${esc(m.first_name)}</a></td><td>${esc(m.middle_name||'')}</td><td>${esc(m.last_name)}</td><td>${esc(m.phone||'')}</td><td>${esc(m.email)}</td></tr>`).join('');
document.querySelectorAll('input[name="sel"]').forEach(i=>i.onchange=()=>selected=Number(i.value));}
addBtn.onclick=()=>dlg.showModal();cancel.onclick=()=>dlg.close();
frm.onsubmit=async(e)=>{e.preventDefault();const p=Object.fromEntries(new FormData(frm).entries());if(!p.middle_name) delete p.middle_name;if(!p.phone) delete p.phone;const r=await fetch('/api/members',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){status.textContent='Create failed';status.className='status err';return;}dlg.close();status.textContent='Member created';status.className='status';load();};
delBtn.onclick=async()=>{if(!selected){status.textContent='Select a member first';status.className='status err';return;}const r=await fetch('/api/members/'+selected,{method:'DELETE'});if(!r.ok){status.textContent='Delete failed';status.className='status err';return;}selected=null;status.textContent='Deleted';status.className='status';load();};
load();
</script></body></html>
"""
    return html.replace("__CSS__", COMMON_CSS)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail_page(project_id: int) -> str:
    html = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Project Detail</title><style>__CSS__</style></head>
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/projects">Projects</a><a href="/members">Members</a></div>
<h1>Project Detail</h1><div id="card" class="card"></div>
<h2>Members</h2>
<div class="toolbar"><select id="memberLookup"></select><button class="primary" id="addMember">Add Member via Lookup</button></div>
<table><thead><tr><th>First-name</th><th>Middle-name</th><th>Last-name</th><th>Email</th></tr></thead><tbody id="memberRows"></tbody></table><p id="status" class="status"></p>
</div>
<script>
const pid=__PID__,card=document.getElementById('card'),rows=document.getElementById('memberRows'),lookup=document.getElementById('memberLookup'),status=document.getElementById('status');
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function load(){const r=await fetch('/api/projects/'+pid);if(!r.ok){card.innerHTML='<p class="err">Project not found</p>';return;}const p=await r.json();
card.innerHTML=`<p><strong>Name:</strong> ${esc(p.name)}</p><p><strong>Description:</strong> ${esc(p.description)}</p><p><strong>Date Created:</strong> ${p.date_created}</p>`;
rows.innerHTML=(p.members||[]).map(m=>`<tr><td><a href="/members/${m.id}">${esc(m.first_name)}</a></td><td>${esc(m.middle_name||'')}</td><td>${esc(m.last_name)}</td><td>${esc(m.email)}</td></tr>`).join('')||'<tr><td colspan="4" class="muted">No members assigned.</td></tr>';
const all=await (await fetch('/api/members')).json();const ids=new Set((p.members||[]).map(m=>m.id));const options=all.filter(m=>!ids.has(m.id));
lookup.innerHTML=options.map(m=>`<option value="${m.id}">${esc(m.first_name)} ${esc(m.middle_name||'')} ${esc(m.last_name)} (${esc(m.email)})</option>`).join('')||'<option value="">No available members</option>';
}
addMember.onclick=async()=>{if(!lookup.value) return;const r=await fetch('/api/projects/'+pid+'/members',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({member_id:Number(lookup.value)})});if(!r.ok){status.textContent='Add member failed';status.className='status err';return;}status.textContent='Member added';status.className='status';load();};
load();
</script></body></html>
"""
    return html.replace("__CSS__", COMMON_CSS).replace("__PID__", str(project_id))


@app.get("/members/{member_id}", response_class=HTMLResponse)
def member_detail_page(member_id: int) -> str:
    html = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Member Detail</title><style>__CSS__</style></head>
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/projects">Projects</a><a href="/members">Members</a></div>
<h1>Member Detail</h1><div id="card" class="card"></div>
<h2>Projects</h2><table><thead><tr><th>Name</th><th>Description</th><th>Date Created</th></tr></thead><tbody id="projRows"></tbody></table>
</div><script>
const mid=__MID__,card=document.getElementById('card'),rows=document.getElementById('projRows');
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function load(){const r=await fetch('/api/members/'+mid);if(!r.ok){card.innerHTML='<p class="err">Member not found</p>';return;}const m=await r.json();
card.innerHTML=`<p><strong>First-name:</strong> ${esc(m.first_name)}</p><p><strong>Middle-name:</strong> ${esc(m.middle_name||'')}</p><p><strong>Last-name:</strong> ${esc(m.last_name)}</p><p><strong>Phone:</strong> ${esc(m.phone||'')}</p><p><strong>Email:</strong> ${esc(m.email)}</p>`;
rows.innerHTML=(m.projects||[]).map(p=>`<tr><td><a href="/projects/${p.id}">${esc(p.name)}</a></td><td>${esc(p.description)}</td><td>${p.date_created}</td></tr>`).join('')||'<tr><td colspan="3" class="muted">No project memberships yet.</td></tr>';
}
load();
</script></body></html>
"""
    return html.replace("__CSS__", COMMON_CSS).replace("__MID__", str(member_id))


def _project_dict(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "date_created": project.date_created.isoformat(),
    }


def _member_dict(member: Member) -> dict:
    return {
        "id": member.id,
        "first_name": member.first_name,
        "middle_name": member.middle_name,
        "last_name": member.last_name,
        "phone": member.phone,
        "email": member.email,
    }


@app.get("/api/projects")
def list_projects() -> list[dict]:
    with SessionLocal() as db:
        projects = db.query(Project).order_by(Project.date_created.desc(), Project.id.desc()).all()
        return [_project_dict(p) for p in projects]


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate) -> dict:
    with SessionLocal() as db:
        project = Project(name=payload.name.strip(), description=payload.description.strip(), date_created=payload.date_created)
        db.add(project)
        db.commit()
        db.refresh(project)
        return _project_dict(project)


@app.get("/api/projects/{project_id}")
def get_project(project_id: int) -> dict:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {**_project_dict(project), "members": [_member_dict(m) for m in project.members]}


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: int) -> None:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        db.delete(project)
        db.commit()


@app.post("/api/projects/{project_id}/members", status_code=201)
def add_project_member(project_id: int, payload: ProjectMemberLink) -> dict:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        member = db.get(Member, payload.member_id)
        if not project or not member:
            raise HTTPException(status_code=404, detail="Project or member not found")
        if member in project.members:
            return {"status": "already-linked"}
        project.members.append(member)
        db.commit()
        return {"status": "linked"}


@app.get("/api/members")
def list_members() -> list[dict]:
    with SessionLocal() as db:
        members = db.query(Member).order_by(Member.last_name.asc(), Member.first_name.asc()).all()
        return [_member_dict(m) for m in members]


@app.post("/api/members", status_code=201)
def create_member(payload: MemberCreate) -> dict:
    with SessionLocal() as db:
        if db.query(Member).filter(Member.email == str(payload.email)).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        member = Member(
            first_name=payload.first_name.strip(),
            middle_name=payload.middle_name.strip() if payload.middle_name else None,
            last_name=payload.last_name.strip(),
            phone=payload.phone.strip() if payload.phone else None,
            email=str(payload.email).strip(),
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return _member_dict(member)


@app.get("/api/members/{member_id}")
def get_member(member_id: int) -> dict:
    with SessionLocal() as db:
        member = db.get(Member, member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        return {**_member_dict(member), "projects": [_project_dict(p) for p in member.projects]}


@app.delete("/api/members/{member_id}", status_code=204)
def delete_member(member_id: int) -> None:
    with SessionLocal() as db:
        member = db.get(Member, member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        db.delete(member)
        db.commit()
