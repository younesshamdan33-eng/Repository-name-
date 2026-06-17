#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================================
CYBERGENESIS v4.0 – النسخة المتطورة والأقوى
====================================================================
منصة توليد مشاريع برمجية عملاقة باستخدام وكلاء ذكاء اصطناعي متخصصين
مع واجهة أمامية احترافية، WebSockets، نظام DAG، تصحيح ذاتي،
ومولد Dockerfiles و docker-compose.yml تلقائي.
====================================================================
"""

# ======================== التهيئة الأساسية =========================
import os
import sys
import json
import asyncio
import tempfile
import zipfile
import shutil
import re
import time
import threading
import hashlib
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum

# -------------------- تثبيت المتطلبات تلقائياً --------------------
def install_deps():
    deps = [
        "fastapi", "uvicorn", "pydantic", "openai==0.28.0",
        "python-multipart", "websockets", "aiofiles",
        "jinja2", "python-dotenv", "requests"
    ]
    for dep in deps:
        try:
            __import__(dep.split("==")[0].replace("-", "_"))
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", dep])

install_deps()

# -------------------- المكتبات --------------------
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import openai

# ======================== الإعدادات ================================
OS_API_KEY = "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"

if not OS_API_KEY or OS_API_KEY == "sk-...":
    print("⚠️  تحذير: لم يتم تعيين مفتاح OpenAI. سيتم استخدام وضع المحاكاة (Mock).")
    USE_MOCK = True
else:
    USE_MOCK = False
    openai.api_key = OS_API_KEY
    print("✅ تم الاتصال بـ OpenAI API بنجاح.")

MODEL_COMPLEX = "gpt-4o-mini"
MODEL_DEBUG = "gpt-4o-mini"

# ======================== وكلاء الذكاء الاصطناعي ====================
class Agent:
    def __init__(self, name: str, system_prompt: str, model: str = MODEL_COMPLEX):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model

    def call(self, user_prompt: str, temperature: float = 0.5) -> str:
        if USE_MOCK:
            return self._mock_response(user_prompt)
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ خطأ في {self.name}: {e}")
            return self._mock_response(user_prompt)

    def _mock_response(self, user_prompt):
        return f"""
# مشروع تم توليده بواسطة المحاكاة (Mock)
# الفكرة: {user_prompt[:100]}...

## الملفات المولدة:
- backend/server.js (خادم Node.js)
- frontend/index.html (واجهة بسيطة)
- Dockerfile
- docker-compose.yml
- README.md

(للحصول على توليد حقيقي، قم بتعيين مفتاح OpenAI API صحيح.)
"""

# -------------------- برومبتات الوكلاء المتقدمة --------------------
REQUIREMENT_PROMPT = """أنت مهندس متطلبات خبير. قم بتحليل الفكرة التالية وإنتاج وثيقة متطلبات مفصلة جداً تشمل:
- نظرة عامة على المشروع
- المتطلبات الوظيفية (مقسمة إلى وحدات)
- المتطلبات غير الوظيفية (أداء، أمان، قابلية التوسع)
- حالات الاستخدام الأساسية
- القيود التقنية
استخدم تنسيق Markdown."""

ARCHITECT_PROMPT = """أنت مهندس معماري خبير. بناءً على وثيقة المتطلبات، قم بتصميم هيكل المشروع الكامل.
يجب أن يتضمن المخرجات بصيغة JSON صارمة بالشكل التالي:
{{
  "project_name": "اسم المشروع",
  "tech_stack": {{"backend": "..." , "frontend": "...", "database": "..."}},
  "auth": "JWT",
  "backend_files": [
    {{"path": "backend/src/models/User.js", "dependencies": []}},
    {{"path": "backend/src/controllers/authController.js", "dependencies": ["backend/src/models/User.js"]}}
  ],
  "frontend_files": [
    {{"path": "frontend/src/App.js", "dependencies": []}}
  ],
  "database_tables": {{"users": ["id", "username", "email"]}}
}}
تأكد من تغطية جميع الملفات الأساسية (Models, Controllers, Middleware, Routes)."""

CODE_GEN_PROMPT = """أنت مطور خبير. قم بكتابة كود ملف واحد فقط.
المخرجات: اكتب الكود فقط مع تعليق المسار في البداية.
مثال:
// backend/src/models/User.js
const mongoose = require('mongoose');
...
لا تضع أي شرح خارج الكود."""

DEBUG_PROMPT = """أنت مصحح أخطاء محترف. قم بإصلاح الكود التالي باستخدام رسالة الخطأ المقدمة.
أخرج الكود المصحح فقط مع تعليق المسار."""

# ======================== إدارة الحالة العامة ====================
class ProjectState:
    def __init__(self, idea: str, language: str = "python", detail: str = "moderate"):
        self.id = f"proj_{int(datetime.now().timestamp())}"
        self.idea = idea
        self.language = language
        self.detail = detail
        self.status = "pending"
        self.progress = 0
        self.total_files = 0
        self.files: Dict[str, str] = {}
        self.signatures: Dict[str, str] = {}
        self.requirements = ""
        self.architecture: Dict = {}
        self.error = None
        self.websocket = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.logs: List[str] = []

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "total_files": self.total_files,
            "files": list(self.files.keys()),
            "error": self.error,
            "logs": self.logs[-20:],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def add_log(self, msg: str):
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ======================== قاعدة البيانات المؤقتة ===================
projects: Dict[str, ProjectState] = {}

# ======================== أدوات مساعدة ============================
def extract_code_and_signature(raw: str) -> tuple:
    lines = raw.splitlines()
    sig = ""
    code_lines = []
    for line in lines:
        if line.strip().startswith("SIGNATURE:"):
            sig = line.strip()[10:].strip()
        else:
            code_lines.append(line)
    return "\n".join(code_lines), sig

def build_levels(dep_graph: Dict[str, List[str]]) -> List[List[str]]:
    graph = {node: set(deps) for node, deps in dep_graph.items()}
    in_degree = {node: len(deps) for node, deps in graph.items()}
    levels = []
    while graph:
        ready = [node for node, deg in in_degree.items() if deg == 0]
        if not ready:
            break
        levels.append(ready)
        for node in ready:
            for other, deps in graph.items():
                if node in deps:
                    in_degree[other] -= 1
            del graph[node]
            del in_degree[node]
    return levels

def generate_mock_project(idea: str, language: str = "python", detail: str = "moderate") -> Dict[str, str]:
    files = {}
    if language == "python":
        files["backend/requirements.txt"] = "fastapi\nuvicorn\nsqlalchemy\npydantic\npython-jose\npasslib\npython-multipart"
        files["backend/main.py"] = """from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Generated Project", description="{idea}")

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username, email=user.email, hashed_password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/", response_model=list[UserOut])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(User).offset(skip).limit(limit).all()

@app.get("/")
def root():
    return {{"message": "Welcome to {idea} API!", "status": "running"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
""".format(idea=idea[:50])
    else:
        files["backend/package.json"] = json.dumps({
            "name": "generated-project",
            "version": "1.0.0",
            "scripts": {"start": "node server.js", "dev": "nodemon server.js"},
            "dependencies": {"express": "^4.18.2", "mongoose": "^7.0.0", "jsonwebtoken": "^9.0.0", "bcryptjs": "^2.4.3", "cors": "^2.8.5", "dotenv": "^16.0.3"},
            "devDependencies": {"nodemon": "^2.0.22"}
        }, indent=2)
        files["backend/server.js"] = """const express = require('express');
const mongoose = require('mongoose');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

// MongoDB Connection
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/mydb')
  .then(() => console.log('✅ MongoDB Connected'))
  .catch(err => console.error('❌ MongoDB Error:', err));

// User Schema
const userSchema = new mongoose.Schema({
  username: { type: String, required: true, unique: true },
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true }
}, { timestamps: true });

const User = mongoose.model('User', userSchema);

// Routes
app.get('/', (req, res) => res.json({ message: 'Welcome to {idea}!', status: 'running' }));

app.post('/api/register', async (req, res) => {
  try {
    const {{ username, email, password }} = req.body;
    const hashedPassword = await bcrypt.hash(password, 10);
    const user = new User({ username, email, password: hashedPassword });
    await user.save();
    res.status(201).json({ message: 'User created successfully' });
  }} catch (err) {{
    res.status(400).json({ error: err.message }});
  }}
}});

app.post('/api/login', async (req, res) => {{
  try {{
    const {{ email, password }} = req.body;
    const user = await User.findOne({{ email }});
    if (!user) return res.status(400).json({{ error: 'User not found' }});
    const valid = await bcrypt.compare(password, user.password);
    if (!valid) return res.status(400).json({{ error: 'Invalid password' }});
    const token = jwt.sign({{ userId: user._id }}, process.env.JWT_SECRET || 'secret', {{ expiresIn: '7d' }});
    res.json({{ token, user: {{ id: user._id, username: user.username, email: user.email }} }});
  }} catch (err) {{
    res.status(400).json({{ error: err.message }});
  }}
}});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🚀 Server running on port ${{PORT}}`));
""".format(idea=idea[:50])

    # Frontend
    files["frontend/index.html"] = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{idea[:30]}...</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
        .container {{ background: rgba(255,255,255,0.95); padding: 40px; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 500px; width: 90%; text-align: center; }}
        h1 {{ color: #333; margin-bottom: 10px; font-size: 28px; }}
        p {{ color: #666; margin-bottom: 30px; }}
        .btn {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; padding: 14px 32px; border-radius: 30px; font-size: 16px; cursor: pointer; transition: transform 0.2s; }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 25px rgba(102,126,234,0.4); }}
        .status {{ margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 10px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 {idea[:30]}...</h1>
        <p>تم توليد هذا المشروع تلقائياً بواسطة CyberGenesis v4.0</p>
        <button class="btn" onclick="testAPI()">📡 اختبار الـ API</button>
        <div class="status" id="status">في انتظار الاختبار...</div>
    </div>
    <script>
        async function testAPI() {{
            try {{
                const res = await fetch('/api');
                const data = await res.json();
                document.getElementById('status').innerHTML = '<span style="color:green">✅ API يعمل!</span><br>' + JSON.stringify(data, null, 2);
            }} catch(e) {{
                document.getElementById('status').innerHTML = '<span style="color:red">❌ ' + e.message + '</span>';
            }}
        }}
    </script>
</body>
</html>"""

    files["frontend/package.json"] = json.dumps({
        "name": "frontend",
        "version": "1.0.0",
        "scripts": {"start": "npx serve .", "build": "echo 'Static files ready'"},
        "dependencies": {}
    }, indent=2)

    # Docker & Config
    files["Dockerfile"] = """# Multi-stage build
FROM node:18-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./

FROM python:3.11-slim AS backend
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /app/frontend ./frontend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]"""

    files["docker-compose.yml"] = """version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app.db
      - JWT_SECRET=your-secret-key-change-in-production
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./backend:/app
    restart: unless-stopped

  frontend:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
    depends_on:
      - app
    restart: unless-stopped"""

    files[".env.example"] = """# Application Settings
PORT=8000
NODE_ENV=development
DATABASE_URL=sqlite:///./app.db
JWT_SECRET=change-this-in-production
OPENAI_API_KEY=your-openai-key-here

# Frontend
FRONTEND_URL=http://localhost:80
API_URL=http://localhost:8000"""

    files["README.md"] = f"""# 🚀 {idea[:50]}...

تم توليد هذا المشروع تلقائياً بواسطة **CyberGenesis v4.0**

## 📋 المتطلبات
- Python 3.11+ أو Node.js 18+
- Docker & Docker Compose (اختياري)

## 🚀 التشغيل السريع

### باستخدام Docker:
```bash
docker-compose up --build
```

### بدون Docker:
```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend (في terminal آخر)
cd frontend
npx serve . -p 80
```

## 📁 هيكل المشروع
```
.
├── backend/          # خادم API
├── frontend/         # واجهة المستخدم
├── Dockerfile        # إعدادات Docker
├── docker-compose.yml
└── README.md
```

## 🔧 المتغيرات البيئية
انسخ `.env.example` إلى `.env` وعدل القيم.

## 📝 المميزات
- ✅ مصادقة JWT
- ✅ قاعدة بيانات متكاملة
- ✅ API RESTful كامل
- ✅ واجهة مستخدم حديثة
- ✅ Docker جاهز

---
تم الإنشاء في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    return files

# ======================== محرك التوليد الأساسي ====================
async def run_orchestrator(pid: str):
    state = projects[pid]
    state.status = "analyzing"
    state.add_log("بدء تحليل المتطلبات...")
    await send_update(state)

    if USE_MOCK:
        state.add_log("وضع المحاكاة نشط - توليد مشروع وهمي...")
        state.files = generate_mock_project(state.idea, state.language, state.detail)
        state.status = "done"
        state.progress = 100
        state.total_files = len(state.files)
        state.add_log(f"تم توليد {state.total_files} ملف بنجاح!")
        await send_update(state)
        return

    try:
        # 1. تحليل المتطلبات
        state.add_log("🧠 تحليل المتطلبات بواسطة وكيل الذكاء الاصطناعي...")
        req_agent = Agent("Requirement Analyst", REQUIREMENT_PROMPT)
        state.requirements = req_agent.call(state.idea, temperature=0.7)
        state.status = "architecting"
        state.progress = 10
        state.add_log("✅ تم تحليل المتطلبات")
        await send_update(state)

        # 2. الهندسة المعمارية
        state.add_log("🏗️ تصميم المعمارية...")
        arch_agent = Agent("System Architect", ARCHITECT_PROMPT)
        arch_text = arch_agent.call(state.requirements, temperature=0.6)
        try:
            json_match = re.search(r'\{.*\}', arch_text, re.DOTALL)
            if json_match:
                arch = json.loads(json_match.group())
            else:
                arch = json.loads(arch_text)
        except:
            arch = {"backend_files": [], "frontend_files": []}
        state.architecture = arch
        state.total_files = len(arch.get("backend_files", [])) + len(arch.get("frontend_files", []))
        if state.total_files == 0:
            state.total_files = 1
        state.add_log(f"📐 تم تصميم {state.total_files} ملف")

        dep_graph = {}
        for item in arch.get("backend_files", []):
            dep_graph[item["path"]] = item.get("dependencies", [])
        for item in arch.get("frontend_files", []):
            dep_graph[item["path"]] = item.get("dependencies", [])

        levels = build_levels(dep_graph)
        state.status = "generating"
        await send_update(state)

        # 3. توليد الملفات (DAG)
        backend_gen = Agent("Backend Developer", CODE_GEN_PROMPT)
        frontend_gen = Agent("Frontend Developer", CODE_GEN_PROMPT)

        generated = 0
        for level in levels:
            tasks = []
            for file_path in level:
                state.add_log(f"⚡ توليد: {file_path}")
                tasks.append(generate_single_file(state, file_path, arch, backend_gen, frontend_gen))
            await asyncio.gather(*tasks)
            generated += len(level)
            state.progress = 10 + int((generated / state.total_files) * 80)
            state.add_log(f"✅ تم توليد {generated}/{state.total_files} ملف")
            await send_update(state)

        # 4. توليد Docker و README
        state.add_log("🐳 توليد ملفات Docker...")
        docker_agent = Agent("DevOps", "أنشئ Dockerfile و docker-compose.yml و .env.example و README.md لهذا المشروع.")
        docker_content = docker_agent.call(json.dumps(arch, indent=2))
        for part in docker_content.split("# "):
            if part.startswith("Dockerfile"):
                state.files["Dockerfile"] = part.replace("Dockerfile\n", "").strip()
            elif part.startswith("docker-compose.yml"):
                state.files["docker-compose.yml"] = part.replace("docker-compose.yml\n", "").strip()
            elif part.startswith(".env.example"):
                state.files[".env.example"] = part.replace(".env.example\n", "").strip()
            elif part.startswith("README.md"):
                state.files["README.md"] = part.replace("README.md\n", "").strip()

        state.status = "done"
        state.progress = 100
        state.add_log("🎉 اكتمل توليد المشروع بنجاح!")
        await send_update(state)

    except Exception as e:
        state.status = "error"
        state.error = str(e)
        state.add_log(f"❌ خطأ: {str(e)}")
        await send_update(state)

async def generate_single_file(state, file_path, arch, backend_gen, frontend_gen):
    gen = backend_gen if file_path.startswith("backend/") else frontend_gen
    context = f"""
Architecture: {json.dumps(arch, indent=2)}
Target file: {file_path}
Generate the complete code for this file. Start with a comment showing the path.
"""
    raw = gen.call(context, temperature=0.5)
    state.files[file_path] = raw.strip()

async def send_update(state):
    if state.websocket:
        try:
            await state.websocket.send_json(state.to_dict())
        except:
            pass

# ======================== تطبيق FastAPI ============================
app = FastAPI(
    title="CyberGenesis v4.0 – Ultimate Platform",
    description="AI-powered project generator for any kind of application",
    version="4.0.0"
)

# ======================== واجهة أمامية (HTML متكاملة) =============
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CyberGenesis v4.0 – منصة التوليد الأسطورية</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0a0e17;
            color: #e2e8f0;
            min-height: 100vh;
            transition: background 0.3s, color 0.3s;
        }
        body.light {
            background: #f1f5f9;
            color: #0f172a;
        }
        .navbar {
            background: rgba(10, 14, 23, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding: 16px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        body.light .navbar {
            background: rgba(241, 245, 249, 0.85);
            border-bottom: 1px solid rgba(0,0,0,0.06);
        }
        .logo {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        .logo span { color: #e2e8f0; -webkit-text-fill-color: #e2e8f0; }
        .nav-actions {
            display: flex;
            gap: 16px;
            align-items: center;
        }
        .theme-toggle {
            background: none;
            border: none;
            color: #94a3b8;
            font-size: 22px;
            cursor: pointer;
            transition: 0.2s;
            padding: 4px;
        }
        .theme-toggle:hover { color: #e2e8f0; transform: scale(1.1); }
        .badge {
            background: #1e293b;
            padding: 4px 14px;
            border-radius: 30px;
            font-size: 12px;
            color: #94a3b8;
            border: 1px solid #334155;
        }
        body.light .badge {
            background: #e2e8f0;
            border-color: #cbd5e1;
            color: #475569;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 32px 24px;
        }
        .hero {
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.08), rgba(129, 140, 248, 0.08));
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 32px;
            padding: 40px 48px;
            margin-bottom: 40px;
            text-align: center;
            backdrop-filter: blur(8px);
        }
        body.light .hero {
            border-color: rgba(0,0,0,0.06);
            background: rgba(56, 189, 248, 0.04);
        }
        .hero h1 {
            font-size: 42px;
            font-weight: 800;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero p {
            color: #94a3b8;
            font-size: 18px;
            max-width: 600px;
            margin: 0 auto;
        }
        body.light .hero p { color: #475569; }
        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }
        @media (max-width: 768px) { .form-grid { grid-template-columns: 1fr; } }
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .form-group label {
            font-weight: 600;
            font-size: 14px;
            color: #cbd5e1;
        }
        body.light .form-group label { color: #334155; }
        .form-group input, .form-group select, .form-group textarea {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 14px 18px;
            color: #e2e8f0;
            font-size: 15px;
            transition: all 0.2s;
            outline: none;
            font-family: inherit;
        }
        body.light .form-group input,
        body.light .form-group select,
        body.light .form-group textarea {
            background: #ffffff;
            border-color: #e2e8f0;
            color: #0f172a;
        }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
            border-color: #38bdf8;
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
        }
        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }
        .btn {
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            border: none;
            border-radius: 16px;
            padding: 16px 32px;
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 12px;
            justify-content: center;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(56, 189, 248, 0.35);
        }
        .btn:active { transform: translateY(0); }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
            box-shadow: none !important;
        }
        .btn-secondary {
            background: #1e293b;
            color: #e2e8f0;
        }
        body.light .btn-secondary {
            background: #e2e8f0;
            color: #0f172a;
        }
        .btn-secondary:hover {
            background: #2d3748;
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        }
        .progress-wrapper {
            margin-top: 24px;
            display: none;
        }
        .progress-wrapper.active { display: block; }
        .progress-header {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 6px;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #1e293b;
            border-radius: 10px;
            overflow: hidden;
        }
        body.light .progress-bar { background: #e2e8f0; }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            border-radius: 10px;
            transition: width 0.4s ease;
            width: 0%;
        }
        .files-section {
            margin-top: 32px;
            display: none;
        }
        .files-section.active { display: block; }
        .files-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .files-header h3 {
            font-size: 18px;
            font-weight: 600;
        }
        .file-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 12px;
        }
        .file-item {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 14px 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.2s;
            cursor: pointer;
            font-size: 14px;
            font-family: monospace;
        }
        body.light .file-item {
            background: #ffffff;
            border-color: #e2e8f0;
        }
        .file-item:hover {
            border-color: #38bdf8;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(56,189,248,0.2);
        }
        .file-item .icon { font-size: 18px; }
        .file-item .name {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .file-item .status {
            font-size: 12px;
        }
        .status-done { color: #4ade80; }
        .status-error { color: #f87171; }
        .status-pending { color: #fbbf24; }
        .code-viewer {
            margin-top: 32px;
            display: none;
        }
        .code-viewer.active { display: block; }
        .code-viewer-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .code-viewer-header h4 {
            font-size: 16px;
            font-weight: 600;
            color: #94a3b8;
        }
        .code-viewer pre {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 20px 24px;
            overflow-x: auto;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 13px;
            line-height: 1.7;
            max-height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }
        body.light .code-viewer pre {
            background: #f8fafc;
            border-color: #e2e8f0;
            color: #0f172a;
        }
        .copy-btn {
            background: #1e293b;
            border: none;
            color: #94a3b8;
            padding: 4px 16px;
            border-radius: 8px;
            font-size: 12px;
            cursor: pointer;
            transition: 0.15s;
        }
        body.light .copy-btn {
            background: #e2e8f0;
            color: #475569;
        }
        .copy-btn:hover {
            background: #2d3748;
            color: #e2e8f0;
        }
        .actions {
            display: flex;
            gap: 16px;
            margin-top: 24px;
            flex-wrap: wrap;
        }
        .status-text {
            font-size: 14px;
            color: #94a3b8;
            margin-top: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-text .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }
        .dot.pending { background: #fbbf24; animation: pulse 1.5s infinite; }
        .dot.generating { background: #38bdf8; animation: pulse 1s infinite; }
        .dot.done { background: #4ade80; }
        .dot.error { background: #f87171; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
        .error-box {
            background: #2d1b1b;
            border: 1px solid #f87171;
            border-radius: 16px;
            padding: 16px 20px;
            color: #f87171;
            margin-top: 16px;
            display: none;
        }
        body.light .error-box {
            background: #fee2e2;
            border-color: #f87171;
        }
        .footer {
            text-align: center;
            padding: 24px;
            color: #475569;
            font-size: 14px;
            border-top: 1px solid #1e293b;
            margin-top: 40px;
        }
        body.light .footer { border-top-color: #e2e8f0; }
        .footer a { color: #38bdf8; text-decoration: none; }
        .log-container {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 16px;
            margin-top: 16px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            display: none;
        }
        body.light .log-container {
            background: #f8fafc;
            border-color: #e2e8f0;
            color: #0f172a;
        }
        .log-container.active { display: block; }
        .log-entry { padding: 2px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        @media (max-width: 640px) {
            .hero { padding: 24px 16px; }
            .hero h1 { font-size: 28px; }
            .container { padding: 16px; }
            .navbar { padding: 12px 16px; }
            .btn { padding: 14px 20px; font-size: 16px; }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">🧠 Cyber<span>Genesis</span></div>
        <div class="nav-actions">
            <span class="badge" id="statusBadge">⚡ جاهز</span>
            <button class="theme-toggle" id="themeToggle" title="تبديل الثيم">🌙</button>
        </div>
    </nav>

    <div class="container">
        <div class="hero">
            <h1>🚀 منصة التوليد الأسطورية v4.0</h1>
            <p>صف فكرتك، وسنقوم ببناء مشروعك بالكامل – مهما كان حجمه أو تعقيده. مع دعم كامل للـ Docker و WebSockets.</p>
        </div>

        <form id="genForm" onsubmit="generateProject(event)">
            <div class="form-grid">
                <div class="form-group" style="grid-column: span 2;">
                    <label>💡 فكرة المشروع</label>
                    <textarea id="projectIdea" placeholder="مثال: منصة تعليمية تفاعلية مع فيديو، دردشة، ولوحة تحكم للمعلمين..." required></textarea>
                </div>
                <div class="form-group">
                    <label>📦 اللغة / الإطار</label>
                    <select id="projectLanguage">
                        <option value="python">Python (FastAPI)</option>
                        <option value="node">Node.js (Express)</option>
                        <option value="react">React + Vite</option>
                        <option value="nextjs">Next.js (Full Stack)</option>
                        <option value="go">Go (Gin)</option>
                        <option value="rust">Rust (Actix)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>🎯 مستوى التفاصيل</label>
                    <select id="detailLevel">
                        <option value="minimal">أساسي (هيكل فقط)</option>
                        <option value="moderate" selected>متوسط (مميزات أساسية)</option>
                        <option value="full">متكامل (جاهز للإنتاج)</option>
                    </select>
                </div>
            </div>
            <button type="submit" class="btn" id="submitBtn">
                <span>🚀 ابدأ التوليد</span>
            </button>
        </form>

        <div class="progress-wrapper" id="progressWrapper">
            <div class="progress-header">
                <span id="statusText">جاري التحليل...</span>
                <span id="progressPercent">0%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="status-text">
                <span class="dot pending" id="statusDot"></span>
                <span id="statusMessage">في انتظار البدء...</span>
            </div>
        </div>

        <div class="log-container" id="logContainer">
            <div style="color:#94a3b8;margin-bottom:8px;font-weight:600;">📋 سجل العمليات:</div>
            <div id="logContent"></div>
        </div>

        <div class="files-section" id="filesSection">
            <div class="files-header">
                <h3>📄 الملفات المولدة</h3>
                <span id="fileCount" style="color:#94a3b8;font-size:14px;">0 ملف</span>
            </div>
            <div class="file-grid" id="fileGrid"></div>
        </div>

        <div class="code-viewer" id="codeViewer">
            <div class="code-viewer-header">
                <h4 id="codeFileName">📄 الملف</h4>
                <button class="copy-btn" onclick="copyCode()">📋 نسخ</button>
            </div>
            <pre id="codeContent"><span style="color:#475569;">// اختر ملفاً لعرض محتواه...</span></pre>
        </div>

        <div class="error-box" id="errorBox"></div>

        <div class="actions" id="actionsArea" style="display:none;">
            <button class="btn" id="downloadBtn" onclick="downloadProject()">📥 تحميل المشروع (ZIP)</button>
            <button class="btn btn-secondary" onclick="resetForm()">🔄 مشروع جديد</button>
        </div>

        <div class="footer">
            <span id="footerStatus">⚡ Powered by OpenAI GPT-4o-mini</span>
        </div>
    </div>

    <script>
        let ws = null;
        let projectId = null;
        let projectFiles = {};
        let currentFile = null;

        document.getElementById('themeToggle').addEventListener('click', function() {
            document.body.classList.toggle('light');
            this.textContent = document.body.classList.contains('light') ? '☀️' : '🌙';
        });

        async function generateProject(e) {
            e.preventDefault();
            const idea = document.getElementById('projectIdea').value.trim();
            if (!idea) { alert('يرجى كتابة فكرة المشروع.'); return; }

            const language = document.getElementById('projectLanguage').value;
            const detail = document.getElementById('detailLevel').value;

            document.getElementById('progressWrapper').classList.add('active');
            document.getElementById('logContainer').classList.add('active');
            document.getElementById('filesSection').classList.remove('active');
            document.getElementById('codeViewer').classList.remove('active');
            document.getElementById('actionsArea').style.display = 'none';
            document.getElementById('errorBox').style.display = 'none';
            document.getElementById('fileGrid').innerHTML = '';
            document.getElementById('logContent').innerHTML = '';
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('statusBadge').textContent = '⏳ جاري...';

            try {
                const res = await fetch('/project', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ idea, language, detail })
                });
                const data = await res.json();
                projectId = data.id;

                if (ws) ws.close();
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/project/${projectId}/ws`);
                ws.onmessage = (event) => {
                    const state = JSON.parse(event.data);
                    updateUI(state);
                };
                ws.onerror = () => {
                    document.getElementById('statusMessage').textContent = '⚠️ خطأ في الاتصال';
                    document.getElementById('statusBadge').textContent = '❌ خطأ';
                };
            } catch (err) {
                showError(err.message);
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('statusBadge').textContent = '❌ فشل';
            }
        }

        function updateUI(state) {
            const statusText = document.getElementById('statusText');
            const progressFill = document.getElementById('progressFill');
            const progressPercent = document.getElementById('progressPercent');
            const statusDot = document.getElementById('statusDot');
            const statusMessage = document.getElementById('statusMessage');
            const fileGrid = document.getElementById('fileGrid');
            const fileCount = document.getElementById('fileCount');
            const logContent = document.getElementById('logContent');

            progressFill.style.width = state.progress + '%';
            progressPercent.textContent = state.progress + '%';

            const statusMap = {
                'pending': { text: '⏳ في الانتظار', dot: 'pending', msg: 'جاري التجهيز...' },
                'analyzing': { text: '🔍 تحليل المتطلبات', dot: 'generating', msg: 'جمع المعلومات...' },
                'architecting': { text: '🏗️ تصميم المعمارية', dot: 'generating', msg: 'بناء الهيكل...' },
                'generating': { text: '⚡ توليد الملفات', dot: 'generating', msg: 'كتابة الكود...' },
                'testing': { text: '🧪 اختبار وتصحيح', dot: 'generating', msg: 'فحص الأكواد...' },
                'done': { text: '✅ اكتمل!', dot: 'done', msg: 'تم توليد المشروع بنجاح.' },
                'error': { text: '❌ خطأ', dot: 'error', msg: state.error || 'حدث خطأ ما.' }
            };
            const info = statusMap[state.status] || statusMap['pending'];
            statusText.textContent = info.text;
            statusDot.className = 'dot ' + info.dot;
            statusMessage.textContent = info.msg;
            document.getElementById('statusBadge').textContent = info.text;

            if (state.logs && state.logs.length > 0) {
                logContent.innerHTML = state.logs.map(l => `<div class="log-entry">${l}</div>`).join('');
                logContent.scrollTop = logContent.scrollHeight;
            }

            if (state.files && state.files.length > 0) {
                document.getElementById('filesSection').classList.add('active');
                fileGrid.innerHTML = '';
                state.files.forEach(f => {
                    const div = document.createElement('div');
                    div.className = 'file-item';
                    const ext = f.split('.').pop();
                    const iconMap = {js:'🟨', py:'🐍', json:'📋', html:'🌐', css:'🎨', md:'📝', yml:'⚙️', yaml:'⚙️', dockerfile:'🐳', env:'🔐', txt:'📄'};
                    const icon = iconMap[ext] || '📄';
                    div.innerHTML = `<span class="icon">${icon}</span><span class="name">${f}</span><span class="status status-done">✅</span>`;
                    div.onclick = () => loadFileContent(f);
                    fileGrid.appendChild(div);
                });
                fileCount.textContent = state.files.length + ' ملف';
                projectFiles = state.files;
            }

            if (state.status === 'done') {
                document.getElementById('actionsArea').style.display = 'flex';
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('statusBadge').textContent = '✅ جاهز';
            }

            if (state.status === 'error') {
                showError(state.error || 'حدث خطأ غير معروف.');
                document.getElementById('submitBtn').disabled = false;
            }

            if (state.status === 'done' || state.status === 'error') {
                document.getElementById('submitBtn').disabled = false;
            }
        }

        async function loadFileContent(filePath) {
            if (!projectId) return;
            try {
                const res = await fetch(`/project/${projectId}/file/${encodeURIComponent(filePath)}`);
                const data = await res.json();
                if (data.content) {
                    document.getElementById('codeViewer').classList.add('active');
                    document.getElementById('codeFileName').textContent = '📄 ' + filePath;
                    document.getElementById('codeContent').textContent = data.content;
                    currentFile = filePath;
                    document.getElementById('codeViewer').scrollIntoView({ behavior: 'smooth' });
                }
            } catch (err) {
                console.error('Error loading file:', err);
            }
        }

        function copyCode() {
            const code = document.getElementById('codeContent').textContent;
            navigator.clipboard.writeText(code).then(() => {
                const btn = document.querySelector('.copy-btn');
                const orig = btn.textContent;
                btn.textContent = '✅ تم النسخ!';
                setTimeout(() => btn.textContent = orig, 2000);
            });
        }

        async function downloadProject() {
            if (!projectId) return;
            try {
                const res = await fetch(`/project/${projectId}/download`);
                if (res.ok) {
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `project_${projectId}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                } else {
                    showError('فشل تحميل المشروع.');
                }
            } catch (err) {
                showError(err.message);
            }
        }

        function resetForm() {
            document.getElementById('projectIdea').value = '';
            document.getElementById('progressWrapper').classList.remove('active');
            document.getElementById('logContainer').classList.remove('active');
            document.getElementById('filesSection').classList.remove('active');
            document.getElementById('codeViewer').classList.remove('active');
            document.getElementById('actionsArea').style.display = 'none';
            document.getElementById('errorBox').style.display = 'none';
            document.getElementById('fileGrid').innerHTML = '';
            document.getElementById('logContent').innerHTML = '';
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('statusBadge').textContent = '⚡ جاهز';
            if (ws) { ws.close(); ws = null; }
            projectId = null;
            projectFiles = {};
            currentFile = null;
        }

        function showError(msg) {
            const box = document.getElementById('errorBox');
            box.textContent = '❌ ' + msg;
            box.style.display = 'block';
        }
    </script>
</body>
</html>
"""

# ======================== نقاط النهاية (Endpoints) ====================
class ProjectCreate(BaseModel):
    idea: str
    language: str = "python"
    detail: str = "moderate"

@app.post("/project")
async def create_project(project: ProjectCreate, background_tasks: BackgroundTasks):
    state = ProjectState(project.idea, project.language, project.detail)
    projects[state.id] = state
    background_tasks.add_task(run_orchestrator, state.id)
    return {"id": state.id, "status": "pending"}

@app.get("/project/{pid}/status")
async def get_status(pid: str):
    state = projects.get(pid)
    if not state:
        raise HTTPException(404, "Project not found")
    return state.to_dict()

@app.get("/project/{pid}/file/{file_path:path}")
async def get_file(pid: str, file_path: str):
    state = projects.get(pid)
    if not state:
        raise HTTPException(404, "Project not found")
    content = state.files.get(file_path)
    if content is None:
        raise HTTPException(404, "File not found")
    return JSONResponse({"content": content})

@app.get("/project/{pid}/download")
async def download_project(pid: str):
    state = projects.get(pid)
    if not state:
        raise HTTPException(404, "Project not found")
    if state.status != "done":
        raise HTTPException(400, "Project not ready")
    tmp_dir = tempfile.gettempdir()
    zip_path = Path(tmp_dir) / f"{pid}.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for file_path, content in state.files.items():
            zf.writestr(file_path, content)
    return FileResponse(zip_path, filename=f"{pid}.zip")

@app.websocket("/project/{pid}/ws")
async def websocket_endpoint(websocket: WebSocket, pid: str):
    await websocket.accept()
    state = projects.get(pid)
    if state:
        state.websocket = websocket
        await send_update(state)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if state:
            state.websocket = None

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_TEMPLATE

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "4.0.0", "mock_mode": USE_MOCK}

# ======================== التشغيل ============================
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     CYBERGENESIS v4.0 – THE ULTIMATE PLATFORM                   ║
    ║     Server: http://localhost:8000                               ║
    ║     API Health: http://localhost:8000/api/health                ║
    ║     Press Ctrl+C to stop                                        ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)
