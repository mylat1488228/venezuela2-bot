from fastapi import FastAPI, Request, Form, HTTPException, Depends, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import asyncpg
import os
import hashlib
import secrets
from datetime import datetime, timedelta

app = FastAPI(title="Venezuela2 Dashboard")
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Хранилище сессий (в продакшене лучше Redis)
sessions = {}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.create_pool(os.getenv("DATABASE_URL"))

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Проверка админов (в реальном проекте храните хеши в БД)
    admins = {
        "kunilus": hash_password("748748"),
        "grif228anki": hash_password("245542")
    }
    
    if username in admins and hash_password(password) == admins[username]:
        session_id = secrets.token_urlsafe(32)
        sessions[session_id] = {
            "user": username,
            "expires": datetime.now() + timedelta(hours=24)
        }
        
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session", value=session_id, httponly=True)
        return response
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_id = request.cookies.get("session")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/")
    
    session = sessions[session_id]
    if datetime.now() > session["expires"]:
        del sessions[session_id]
        return RedirectResponse(url="/")
    
    # Получаем статистику
    async with app.state.db.acquire() as conn:
        stats = await conn.fetchrow('''
            SELECT COUNT(*) as users,
                   SUM(messages) as total_messages,
                   SUM(voice_time) as total_voice
            FROM users
        ''')
        
        recent_reports = await conn.fetch('''
            SELECT * FROM reports 
            ORDER BY created_at DESC LIMIT 5
        ''')
        
        open_tickets = await conn.fetch('''
            SELECT * FROM tickets 
            WHERE status = 'open'
            ORDER BY created_at DESC
        ''')
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": session["user"],
        "stats": stats,
        "reports": recent_reports,
        "tickets": open_tickets
    })

@app.get("/api/stats")
async def api_stats():
    """API для получения статистики (для AJAX)"""
    async with app.state.db.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT COUNT(*) as online_users 
            FROM users 
            WHERE last_active > NOW() - INTERVAL '5 minutes'
        ''')
    return {"online": row["online_users"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))