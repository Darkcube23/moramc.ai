from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
import uvicorn

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
def init_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_database()

# Request/Response models
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    token: str

class ChatResponse(BaseModel):
    response: str

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hash: str) -> bool:
    return hash_password(password) == hash

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    conn.commit()
    conn.close()
    return token

def get_user_from_token(token: str) -> Optional[dict]:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username 
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.created_at > datetime('now', '-7 days')
    ''', (token,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"id": user[0], "username": user[1]}
    return None

def get_ai_response(message: str, username: str) -> str:
    """Simple AI response generator - replace with actual AI API"""
    message_lower = message.lower()
    
    responses = {
        "hello": f"Hi {username}! How can I help you today?",
        "hi": f"Hello {username}! Nice to see you.",
        "how are you": "I'm doing great, thanks for asking! How about you?",
        "what is your name": "I'm Morai, your friendly AI assistant!",
        "help": "I can chat with you, answer questions, or just keep you company. What would you like to do?",
        "bye": "Goodbye! Come back anytime!",
        "thanks": "You're very welcome! 😊"
    }
    
    for key, response in responses.items():
        if key in message_lower:
            return response
    
    return f"That's interesting, {username}! Tell me more about '{message}' - I'd love to learn more."

# API Endpoints
@app.post("/register")
async def register(request: RegisterRequest):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        password_hash = hash_password(request.password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (request.username, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        token = create_session(user_id)
        conn.close()
        return {"success": True, "token": token, "message": "Registration successful!"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
async def login(request: LoginRequest):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (request.username,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(request.password, user[1]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_session(user[0])
    return {"success": True, "token": token, "message": "Login successful!"}

@app.post("/chat")
async def chat(request: ChatRequest):
    # Verify user
    user = get_user_from_token(request.token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Save user message
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
        (user["id"], "user", request.message)
    )
    
    # Generate AI response
    ai_response = get_ai_response(request.message, user["username"])
    
    # Save AI response
    cursor.execute(
        "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
        (user["id"], "assistant", ai_response)
    )
    conn.commit()
    conn.close()
    
    return {"response": ai_response}

@app.get("/history/{token}")
async def get_history(token: str):
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, timestamp FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50",
        (user["id"],)
    )
    history = [{"role": row[0], "content": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
    conn.close()
    
    return {"history": history}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)