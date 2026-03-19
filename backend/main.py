import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
import uuid
from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

load_dotenv()
API_KEY = os.getenv("API_KEY")

def require_api_key(x_api_key: str | None):
    if not API_KEY:
        raise RuntimeError("API_KEY not set")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv()

# config JWT token
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "60"))

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET not set")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Capstone API")

class UserCreate(BaseModel):
    username: str
    email: str
    password: str = Field(..., min_length=8, max_length=72)

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token(*, sub: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRE_MIN)
    payload = {"sub": sub, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/db-check")
def db_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"db_ok": True}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tables")
def list_tables():
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SHOW TABLES")).fetchall()
        return {"tables": [r[0] for r in rows]}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users")
def create_user(user: UserCreate, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    try:
        user_id = str(uuid.uuid4())[:15]
        hashed_password = pwd_context.hash(user.password)

        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO users (userid, username, email, password_hash)
                    VALUES (:userid, :username, :email, :password)
                """),
                {
                    "userid": user_id,
                    "username": user.username,
                    "email": user.email,
                    "password": hashed_password 
                }
            )
            conn.commit()

        return {"message": "User created", "userid": user_id}

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=repr(e))
    
@app.get("/users")
def get_users():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT userid, username, email FROM users")).fetchall()
    return {"users": [dict(r._mapping) for r in rows]}

@app.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT userid, password_hash FROM users WHERE email = :email LIMIT 1"),
                {"email": body.email},
            ).fetchone()

        # Generic 401 whether login credentials are valid
        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        userid, password_hash = row[0], row[1]

        if not pwd_context.verify(body.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token(sub=str(userid))
        return {"access_token": token, "token_type": "bearer"}

    except HTTPException:
        raise
    except SQLAlchemyError:
        # Don't leak DB details to client
        raise HTTPException(status_code=500, detail="Database error")