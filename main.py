import csv
import io
import os
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, Date, ForeignKey, Integer, String, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from emails import send_project_membership_email


load_dotenv()


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
.container{max-width:1140px;margin:28px auto;background:#fff;border:1px solid #dbe2ea;border-radius:12px;padding:22px;box-shadow:0 10px 30px rgba(15,23,42,.08)}
.topnav{display:flex;gap:12px;margin-bottom:12px}.topnav a{text-decoration:none;color:#1d4ed8;font-weight:600}
h1{margin:8px 0 18px}.toolbar{display:flex;justify-content:flex-end;gap:10px;margin-bottom:12px;align-items:center;flex-wrap:wrap}
button{border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}.primary{background:#1d4ed8;color:#fff}.danger{background:#dc2626;color:#fff}
table{width:100%;border-collapse:collapse}th,td{border:1px solid #dbe2ea;padding:10px;vertical-align:top}thead th{text-align:left;background:#f8fafc;color:#64748b}
a{color:#1d4ed8}
.status{min-height:1.1rem;color:#64748b}.status.err{color:#b91c1c}
.muted{text-align:center;color:#64748b}
.form{display:grid;gap:10px}.form label{display:grid;gap:6px;font-weight:600}.form input,.form textarea,.form select,select{padding:9px;border:1px solid #cbd5e1;border-radius:8px}
.actions{display:flex;justify-content:flex-end;gap:8px;margin-top:6px}
.card{background:#f8fafc;border:1px solid #dbe2ea;border-radius:10px;padding:14px;margin-bottom:16px}
dialog{border:0;border-radius:12px;box-shadow:0 20px 50px rgba(15,23,42,.25);width:min(640px,94vw)}
"""


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "member_id", name="uq_project_member"),)

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "member_id", name="uq_org_member"),)

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(1000), nullable=True)
    abn = Column(String(64), nullable=True)

    projects = relationship("Project", back_populates="organization")
    members = relationship("Member", secondary="organization_members", back_populates="organizations")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False)
    date_created = Column(Date, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)

    members = relationship("Member", secondary="project_members", back_populates="projects")
    organization = relationship("Organization", back_populates="projects")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(120), nullable=False)
    middle_name = Column(String(120), nullable=True)
    last_name = Column(String(120), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=False, unique=True)

    projects = relationship("Project", secondary="project_members", back_populates="members")
    organizations = relationship("Organization", secondary="organization_members", back_populates="members")


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    date_created: date
    organization_id: Optional[int] = None


class MemberCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    middle_name: Optional[str] = Field(default=None, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: EmailStr


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: Optional[str] = Field(default=None, max_length=1000)
    abn: Optional[str] = Field(default=None, max_length=64)


class ProjectMemberLink(BaseModel):
    member_id: int


class OrganizationMemberLink(BaseModel):
    member_id: int


app = FastAPI(title="CodexActivityApp")


def _migrate_schema_if_needed() -> None:
    """Apply lightweight schema updates for existing databases without Alembic."""
    inspector = inspect(engine)

    if inspector.has_table("projects"):
        project_columns = {col["name"] for col in inspector.get_columns("projects")}
        if "organization_id" not in project_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE projects ADD COLUMN organization_id INTEGER NULL"))


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_schema_if_needed()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Home</title>
<style>body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#eef2f7;color:#0f172a;display:grid;place-items:center;min-height:100vh}.wrap{width:min(980px,92vw)}.title{margin:0;font-size:2rem}.sub{margin:8px 0 20px;color:#64748b}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}.tile{display:block;text-decoration:none;background:#fff;padding:24px;border:1px solid #dbe2ea;border-radius:14px;box-shadow:0 10px 26px rgba(15,23,42,.08)}.tile h2{margin:0 0 8px;color:#1d4ed8}.tile p{margin:0;color:#475569}</style></head>
<body><div class="wrap"><h1 class="title">Business Workspace</h1><p class="sub">Codex built this!</p><div class="tiles"><a class="tile" href="/projects"><h2>Projects</h2><p>Manage projects and assignments.</p></a><a class="tile" href="/members"><h2>Members</h2><p>Manage members and project memberships.</p></a><a class="tile" href="/organizations"><h2>Organization</h2><p>Manage organizations, projects, and member links.</p></a></div></div></body></html>
"""


@app.get("/projects", response_class=HTMLResponse)
def projects_page() -> str:
    html = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Projects</title><style>__CSS__</style></head>
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/members">Members</a><a href="/organizations">Organization</a></div>
<h1>Projects</h1>
<div class="toolbar"><button class="primary" id="addBtn">Add Project</button><button class="danger" id="delBtn">Delete Selected</button></div>
<table><thead><tr><th></th><th>Name</th><th>Description</th><th>Date Created</th><th>Organization</th></tr></thead><tbody id="rows"></tbody></table><p id="status" class="status"></p>
</div>
<dialog id="dlg"><form id="frm" class="form"><h2>Add Project</h2>
<label>Name<input name="name" required maxlength="255"/></label>
<label>Description<textarea name="description" required maxlength="1000"></textarea></label>
<label>Date Created<input type="date" name="date_created" value="__TODAY__" required/></label>
<label>Organization
  <select name="organization_id" id="organization_id"><option value="">No organization</option></select>
</label>
<div class="actions"><button type="button" id="cancel">Cancel</button><button class="primary" type="submit">Save</button></div>
</form></dialog>
<script>
const rows=document.getElementById('rows'),status=document.getElementById('status'),orgSel=document.getElementById('organization_id');let selected=null;
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function loadOrgs(){const r=await fetch('/api/organizations');const data=await r.json();orgSel.innerHTML='<option value="">No organization</option>'+data.map(o=>`<option value="${o.id}">${esc(o.name)}</option>`).join('');}
async function load(){const r=await fetch('/api/projects');const data=await r.json();if(!data.length){rows.innerHTML='<tr><td colspan="5" class="muted">No projects yet.</td></tr>';return;}
rows.innerHTML=data.map(p=>`<tr><td><input type="radio" name="sel" value="${p.id}" ${selected===p.id?'checked':''}></td><td><a href="/projects/${p.id}">${esc(p.name)}</a></td><td>${esc(p.description)}</td><td>${p.date_created}</td><td>${esc(p.organization_name||'')}</td></tr>`).join('');
document.querySelectorAll('input[name="sel"]').forEach(i=>i.onchange=()=>selected=Number(i.value));}
addBtn.onclick=async()=>{await loadOrgs();dlg.showModal();};cancel.onclick=()=>dlg.close();
frm.onsubmit=async(e)=>{e.preventDefault();const payload=Object.fromEntries(new FormData(frm).entries());if(!payload.organization_id) delete payload.organization_id; else payload.organization_id=Number(payload.organization_id);const r=await fetch('/api/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok){status.textContent='Create failed';status.className='status err';return;}dlg.close();status.textContent='Project created';status.className='status';load();};
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
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/projects">Projects</a><a href="/organizations">Organization</a></div>
<h1>Members</h1>
<div class="toolbar"><button class="primary" id="addBtn">Add Member</button><button class="primary" id="importBtn">Import CSV</button><button class="danger" id="delBtn">Delete Selected</button><input id="importFile" type="file" accept=".csv,text/csv" style="display:none" /></div>
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
const rows=document.getElementById('rows'),status=document.getElementById('status'),importBtn=document.getElementById('importBtn'),importFile=document.getElementById('importFile');let selected=null;
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function load(){const r=await fetch('/api/members');const data=await r.json();if(!data.length){rows.innerHTML='<tr><td colspan="6" class="muted">No members yet.</td></tr>';return;}
rows.innerHTML=data.map(m=>`<tr><td><input type="radio" name="sel" value="${m.id}" ${selected===m.id?'checked':''}></td><td><a href="/members/${m.id}">${esc(m.first_name)}</a></td><td>${esc(m.middle_name||'')}</td><td>${esc(m.last_name)}</td><td>${esc(m.phone||'')}</td><td>${esc(m.email)}</td></tr>`).join('');
document.querySelectorAll('input[name="sel"]').forEach(i=>i.onchange=()=>selected=Number(i.value));}
addBtn.onclick=()=>dlg.showModal();cancel.onclick=()=>dlg.close();
importBtn.onclick=()=>importFile.click();
importFile.onchange=async()=>{
  const file=importFile.files && importFile.files[0];
  if(!file) return;
  const formData=new FormData();
  formData.append('file', file);
  const r=await fetch('/api/members/import_csv',{method:'POST',body:formData});
  if(!r.ok){
    const err=await r.text();
    status.textContent='Import failed: '+err;
    status.className='status err';
    importFile.value='';
    return;
  }
  const result=await r.json();
  status.textContent=`Imported ${result.created} member(s), skipped ${result.skipped} row(s).`;
  status.className='status';
  importFile.value='';
  load();
};
frm.onsubmit=async(e)=>{e.preventDefault();const p=Object.fromEntries(new FormData(frm).entries());if(!p.middle_name) delete p.middle_name;if(!p.phone) delete p.phone;const r=await fetch('/api/members',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){status.textContent='Create failed';status.className='status err';return;}dlg.close();status.textContent='Member created';status.className='status';load();};
delBtn.onclick=async()=>{if(!selected){status.textContent='Select a member first';status.className='status err';return;}const r=await fetch('/api/members/'+selected,{method:'DELETE'});if(!r.ok){status.textContent='Delete failed';status.className='status err';return;}selected=null;status.textContent='Deleted';status.className='status';load();};
load();
</script></body></html>
"""
    return html.replace("__CSS__", COMMON_CSS)


@app.get("/organizations", response_class=HTMLResponse)
def organizations_page() -> str:
    html = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Organization</title><style>__CSS__</style></head>
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/projects">Projects</a><a href="/members">Members</a></div>
<h1>Organization</h1>
<div class="toolbar"><button class="primary" id="addBtn">Add Organization</button><button class="danger" id="delBtn">Delete Selected</button></div>
<table><thead><tr><th></th><th>Name</th><th>Address</th><th>ABN</th></tr></thead><tbody id="rows"></tbody></table><p id="status" class="status"></p>
</div>
<dialog id="dlg"><form id="frm" class="form"><h2>Add Organization</h2>
<label>Name<input name="name" required maxlength="255"/></label>
<label>Address (optional)<textarea name="address" maxlength="1000"></textarea></label>
<label>ABN (optional)<input name="abn" maxlength="64"/></label>
<div class="actions"><button type="button" id="cancel">Cancel</button><button class="primary" type="submit">Save</button></div>
</form></dialog>
<script>
const rows=document.getElementById('rows'),status=document.getElementById('status'),importBtn=document.getElementById('importBtn'),importFile=document.getElementById('importFile');let selected=null;
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function load(){const r=await fetch('/api/organizations');const data=await r.json();if(!data.length){rows.innerHTML='<tr><td colspan="4" class="muted">No organizations yet.</td></tr>';return;}
rows.innerHTML=data.map(o=>`<tr><td><input type="radio" name="sel" value="${o.id}" ${selected===o.id?'checked':''}></td><td><a href="/organizations/${o.id}">${esc(o.name)}</a></td><td>${esc(o.address||'')}</td><td>${esc(o.abn||'')}</td></tr>`).join('');
document.querySelectorAll('input[name="sel"]').forEach(i=>i.onchange=()=>selected=Number(i.value));}
addBtn.onclick=()=>dlg.showModal();cancel.onclick=()=>dlg.close();
importBtn.onclick=()=>importFile.click();
importFile.onchange=async()=>{
  const file=importFile.files && importFile.files[0];
  if(!file) return;
  const formData=new FormData();
  formData.append('file', file);
  const r=await fetch('/api/members/import_csv',{method:'POST',body:formData});
  if(!r.ok){
    const err=await r.text();
    status.textContent='Import failed: '+err;
    status.className='status err';
    importFile.value='';
    return;
  }
  const result=await r.json();
  status.textContent=`Imported ${result.created} member(s), skipped ${result.skipped} row(s).`;
  status.className='status';
  importFile.value='';
  load();
};
frm.onsubmit=async(e)=>{e.preventDefault();const p=Object.fromEntries(new FormData(frm).entries());if(!p.address) delete p.address;if(!p.abn) delete p.abn;const r=await fetch('/api/organizations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){status.textContent='Create failed';status.className='status err';return;}dlg.close();status.textContent='Organization created';status.className='status';load();};
delBtn.onclick=async()=>{if(!selected){status.textContent='Select an organization first';status.className='status err';return;}const r=await fetch('/api/organizations/'+selected,{method:'DELETE'});if(!r.ok){status.textContent='Delete failed';status.className='status err';return;}selected=null;status.textContent='Deleted';status.className='status';load();};
load();
</script></body></html>
"""
    return html.replace("__CSS__", COMMON_CSS)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail_page(project_id: int) -> str:
    html = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Project Detail</title><style>__CSS__</style></head>
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/projects">Projects</a><a href="/members">Members</a><a href="/organizations">Organization</a></div>
<h1>Project Detail</h1><div id="card" class="card"></div>
<h2>Members</h2>
<div class="toolbar"><select id="memberLookup"></select><button class="primary" id="addMember">Add Member via Lookup</button></div>
<table><thead><tr><th>First-name</th><th>Middle-name</th><th>Last-name</th><th>Email</th><th>Actions</th></tr></thead><tbody id="memberRows"></tbody></table><p id="status" class="status"></p>
</div>
<script>
const pid=__PID__,card=document.getElementById('card'),rows=document.getElementById('memberRows'),lookup=document.getElementById('memberLookup'),status=document.getElementById('status');
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function load(){const r=await fetch('/api/projects/'+pid);if(!r.ok){card.innerHTML='<p class="err">Project not found</p>';return;}const p=await r.json();
card.innerHTML=`<p><strong>Name:</strong> ${esc(p.name)}</p><p><strong>Description:</strong> ${esc(p.description)}</p><p><strong>Date Created:</strong> ${p.date_created}</p><p><strong>Organization:</strong> ${esc(p.organization_name||'None')}</p>`;
rows.innerHTML=(p.members||[]).map(m=>`<tr><td><a href="/members/${m.id}">${esc(m.first_name)}</a></td><td>${esc(m.middle_name||'')}</td><td>${esc(m.last_name)}</td><td>${esc(m.email)}</td><td><button class="danger" data-remove-member-id="${m.id}">Remove</button></td></tr>`).join('')||'<tr><td colspan="5" class="muted">No members assigned.</td></tr>';
Array.from(document.querySelectorAll('[data-remove-member-id]')).forEach((btn)=>{btn.onclick=async()=>{const mid=Number(btn.getAttribute('data-remove-member-id'));const r=await fetch('/api/projects/'+pid+'/members/'+mid,{method:'DELETE'});if(!r.ok){status.textContent='Remove member failed';status.className='status err';return;}status.textContent='Member removed';status.className='status';load();};});
lookup.innerHTML=(p.lookup_members||[]).map(m=>`<option value="${m.id}">${esc(m.first_name)} ${esc(m.middle_name||'')} ${esc(m.last_name)} (${esc(m.email)})</option>`).join('')||'<option value="">No available members</option>';
}
addMember.onclick=async()=>{if(!lookup.value) return;const r=await fetch('/api/projects/'+pid+'/members',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({member_id:Number(lookup.value)})});if(!r.ok){status.textContent='Add member failed';status.className='status err';return;}status.textContent='Member added';status.className='status';load();};
load();
</script></body></html>
"""
    return html.replace("__CSS__", COMMON_CSS).replace("__PID__", str(project_id))


@app.get("/organizations/{organization_id}", response_class=HTMLResponse)
def organization_detail_page(organization_id: int) -> str:
    html = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Organization Detail</title><style>__CSS__</style></head>
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/organizations">Organization</a><a href="/projects">Projects</a><a href="/members">Members</a></div>
<h1>Organization Detail</h1><div id="card" class="card"></div>
<h2>Projects</h2>
<div class="toolbar"><button class="primary" id="showCreateProject">Create Project</button></div>
<dialog id="projDlg"><form id="projFrm" class="form"><h2>Create Project in Organization</h2>
<label>Name<input name="name" required maxlength="255"/></label>
<label>Description<textarea name="description" required maxlength="1000"></textarea></label>
<label>Date Created<input type="date" name="date_created" value="__TODAY__" required/></label>
<div class="actions"><button type="button" id="cancelProj">Cancel</button><button class="primary" type="submit">Save</button></div>
</form></dialog>
<table><thead><tr><th>Name</th><th>Description</th><th>Date Created</th></tr></thead><tbody id="projRows"></tbody></table>
<h2>Members</h2>
<div class="toolbar"><select id="memberLookup"></select><button class="primary" id="addMember">Add Member via Lookup</button></div>
<table><thead><tr><th>First-name</th><th>Middle-name</th><th>Last-name</th><th>Email</th></tr></thead><tbody id="memberRows"></tbody></table>
<p id="status" class="status"></p></div>
<script>
const oid=__OID__,card=document.getElementById('card'),projRows=document.getElementById('projRows'),memberRows=document.getElementById('memberRows'),lookup=document.getElementById('memberLookup'),status=document.getElementById('status');
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function load(){const r=await fetch('/api/organizations/'+oid);if(!r.ok){card.innerHTML='<p class="err">Organization not found</p>';return;}const o=await r.json();
card.innerHTML=`<p><strong>Name:</strong> ${esc(o.name)}</p><p><strong>Address:</strong> ${esc(o.address||'')}</p><p><strong>ABN:</strong> ${esc(o.abn||'')}</p>`;
projRows.innerHTML=(o.projects||[]).map(p=>`<tr><td><a href="/projects/${p.id}">${esc(p.name)}</a></td><td>${esc(p.description)}</td><td>${p.date_created}</td></tr>`).join('')||'<tr><td colspan="3" class="muted">No projects.</td></tr>';
memberRows.innerHTML=(o.members||[]).map(m=>`<tr><td><a href="/members/${m.id}">${esc(m.first_name)}</a></td><td>${esc(m.middle_name||'')}</td><td>${esc(m.last_name)}</td><td>${esc(m.email)}</td></tr>`).join('')||'<tr><td colspan="4" class="muted">No members linked.</td></tr>';
const all=await (await fetch('/api/members')).json();const ids=new Set((o.members||[]).map(m=>m.id));const avail=all.filter(m=>!ids.has(m.id));
lookup.innerHTML=avail.map(m=>`<option value="${m.id}">${esc(m.first_name)} ${esc(m.middle_name||'')} ${esc(m.last_name)} (${esc(m.email)})</option>`).join('')||'<option value="">No available members</option>';
}
showCreateProject.onclick=()=>projDlg.showModal();cancelProj.onclick=()=>projDlg.close();
projFrm.onsubmit=async(e)=>{e.preventDefault();const p=Object.fromEntries(new FormData(projFrm).entries());p.organization_id=oid;const r=await fetch('/api/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){status.textContent='Project create failed';status.className='status err';return;}projDlg.close();status.textContent='Project created';status.className='status';load();};
addMember.onclick=async()=>{if(!lookup.value) return;const r=await fetch('/api/organizations/'+oid+'/members',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({member_id:Number(lookup.value)})});if(!r.ok){status.textContent='Add member failed';status.className='status err';return;}status.textContent='Member linked';status.className='status';load();};
load();
</script></body></html>
"""
    return html.replace("__CSS__", COMMON_CSS).replace("__OID__", str(organization_id)).replace("__TODAY__", date.today().isoformat())


@app.get("/members/{member_id}", response_class=HTMLResponse)
def member_detail_page(member_id: int) -> str:
    html = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>Member Detail</title><style>__CSS__</style></head>
<body><div class="container"><div class="topnav"><a href="/">← Home</a><a href="/projects">Projects</a><a href="/members">Members</a><a href="/organizations">Organization</a></div>
<h1>Member Detail</h1><div id="card" class="card"></div>
<h2>Projects</h2><table><thead><tr><th>Name</th><th>Description</th><th>Date Created</th></tr></thead><tbody id="projRows"></tbody></table>
<h2>Organizations</h2><table><thead><tr><th>Name</th><th>Address</th><th>ABN</th></tr></thead><tbody id="orgRows"></tbody></table>
</div><script>
const mid=__MID__,card=document.getElementById('card'),rows=document.getElementById('projRows'),orgRows=document.getElementById('orgRows');
function esc(v){return (v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
async function load(){const r=await fetch('/api/members/'+mid);if(!r.ok){card.innerHTML='<p class="err">Member not found</p>';return;}const m=await r.json();
card.innerHTML=`<p><strong>First-name:</strong> ${esc(m.first_name)}</p><p><strong>Middle-name:</strong> ${esc(m.middle_name||'')}</p><p><strong>Last-name:</strong> ${esc(m.last_name)}</p><p><strong>Phone:</strong> ${esc(m.phone||'')}</p><p><strong>Email:</strong> ${esc(m.email)}</p>`;
rows.innerHTML=(m.projects||[]).map(p=>`<tr><td><a href="/projects/${p.id}">${esc(p.name)}</a></td><td>${esc(p.description)}</td><td>${p.date_created}</td></tr>`).join('')||'<tr><td colspan="3" class="muted">No project memberships yet.</td></tr>';
orgRows.innerHTML=(m.organizations||[]).map(o=>`<tr><td><a href="/organizations/${o.id}">${esc(o.name)}</a></td><td>${esc(o.address||'')}</td><td>${esc(o.abn||'')}</td></tr>`).join('')||'<tr><td colspan="3" class="muted">No organization links yet.</td></tr>';
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
        "organization_id": project.organization_id,
        "organization_name": project.organization.name if project.organization else None,
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


def _organization_dict(org: Organization) -> dict:
    return {"id": org.id, "name": org.name, "address": org.address, "abn": org.abn}


@app.get("/api/projects")
def list_projects() -> list[dict]:
    with SessionLocal() as db:
        projects = db.query(Project).order_by(Project.date_created.desc(), Project.id.desc()).all()
        return [_project_dict(p) for p in projects]


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate) -> dict:
    with SessionLocal() as db:
        org_id = payload.organization_id
        if org_id is not None and not db.get(Organization, org_id):
            raise HTTPException(status_code=404, detail="Organization not found")
        project = Project(
            name=payload.name.strip(),
            description=payload.description.strip(),
            date_created=payload.date_created,
            organization_id=org_id,
        )
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

        if project.organization_id:
            org_member_ids = {m.id for m in project.organization.members}
            visible_members = [m for m in project.members if m.id in org_member_ids]
            lookup_members = [m for m in project.organization.members if m.id not in {pm.id for pm in project.members}]
        else:
            visible_members = list(project.members)
            project_member_ids = {m.id for m in project.members}
            lookup_members = [m for m in db.query(Member).all() if m.id not in project_member_ids]

        return {
            **_project_dict(project),
            "members": [_member_dict(m) for m in visible_members],
            "lookup_members": [_member_dict(m) for m in lookup_members],
        }


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
        if project.organization_id and member not in project.organization.members:
            raise HTTPException(status_code=400, detail="Member must belong to the project's organization")
        if member in project.members:
            return {"status": "already-linked"}
        project.members.append(member)
        db.commit()

        send_project_membership_email(
            member_email=member.email,
            member_full_name=f"{member.first_name} {member.last_name}".strip(),
            project_name=project.name,
            project_id=project.id,
            action="added",
        )

        return {"status": "linked"}


@app.delete("/api/projects/{project_id}/members/{member_id}", status_code=204)
def remove_project_member(project_id: int, member_id: int) -> None:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        member = db.get(Member, member_id)
        if not project or not member:
            raise HTTPException(status_code=404, detail="Project or member not found")
        if member not in project.members:
            raise HTTPException(status_code=404, detail="Member is not assigned to project")

        project.members.remove(member)
        db.commit()

        send_project_membership_email(
            member_email=member.email,
            member_full_name=f"{member.first_name} {member.last_name}".strip(),
            project_name=project.name,
            project_id=project.id,
            action="removed",
        )


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


@app.post("/api/members/import_csv")
def import_members_csv(file: UploadFile = File(...)) -> dict:
    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    raw = file.file.read()
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(decoded))
    expected = ["First-name", "Middle-name", "Last-name", "Phone", "Email"]
    if reader.fieldnames != expected:
        raise HTTPException(status_code=400, detail=f"CSV header must be: {','.join(expected)}")

    created = 0
    skipped = 0
    with SessionLocal() as db:
        for row in reader:
            first = (row.get("First-name") or "").strip()
            middle = (row.get("Middle-name") or "").strip() or None
            last = (row.get("Last-name") or "").strip()
            phone = (row.get("Phone") or "").strip() or None
            email = (row.get("Email") or "").strip()

            if not first or not last or not email:
                skipped += 1
                continue

            if db.query(Member).filter(Member.email == email).first():
                skipped += 1
                continue

            db.add(
                Member(
                    first_name=first,
                    middle_name=middle,
                    last_name=last,
                    phone=phone,
                    email=email,
                )
            )
            created += 1

        db.commit()

    return {"created": created, "skipped": skipped}


@app.get("/api/members/{member_id}")
def get_member(member_id: int) -> dict:
    with SessionLocal() as db:
        member = db.get(Member, member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        return {
            **_member_dict(member),
            "projects": [_project_dict(p) for p in member.projects],
            "organizations": [_organization_dict(o) for o in member.organizations],
        }


@app.delete("/api/members/{member_id}", status_code=204)
def delete_member(member_id: int) -> None:
    with SessionLocal() as db:
        member = db.get(Member, member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        db.delete(member)
        db.commit()


@app.get("/api/organizations")
def list_organizations() -> list[dict]:
    with SessionLocal() as db:
        orgs = db.query(Organization).order_by(Organization.name.asc()).all()
        return [_organization_dict(o) for o in orgs]


@app.post("/api/organizations", status_code=201)
def create_organization(payload: OrganizationCreate) -> dict:
    with SessionLocal() as db:
        org = Organization(
            name=payload.name.strip(),
            address=payload.address.strip() if payload.address else None,
            abn=payload.abn.strip() if payload.abn else None,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        return _organization_dict(org)


@app.get("/api/organizations/{organization_id}")
def get_organization(organization_id: int) -> dict:
    with SessionLocal() as db:
        org = db.get(Organization, organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return {
            **_organization_dict(org),
            "projects": [_project_dict(p) for p in org.projects],
            "members": [_member_dict(m) for m in org.members],
        }


@app.post("/api/organizations/{organization_id}/members", status_code=201)
def add_organization_member(organization_id: int, payload: OrganizationMemberLink) -> dict:
    with SessionLocal() as db:
        org = db.get(Organization, organization_id)
        member = db.get(Member, payload.member_id)
        if not org or not member:
            raise HTTPException(status_code=404, detail="Organization or member not found")
        if member in org.members:
            return {"status": "already-linked"}
        org.members.append(member)
        db.commit()
        return {"status": "linked"}


@app.delete("/api/organizations/{organization_id}", status_code=204)
def delete_organization(organization_id: int) -> None:
    with SessionLocal() as db:
        org = db.get(Organization, organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        db.delete(org)
        db.commit()
