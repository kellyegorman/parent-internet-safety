import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
import uuid
from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from typing import Optional

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

class DeviceCreate(BaseModel):
    deviceid: str = Field(..., max_length=15)
    userid: str = Field(..., max_length=15)
    device_name: str = Field(..., max_length=100)
    device_token: Optional[str] = Field(None, max_length=255)

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class SearchCreate(BaseModel):
    deviceid: str
    query_text: str
    url: str | None = None

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
    
@app.post("/devices")
def add_device(payload: DeviceCreate):
    try:
        with engine.begin() as conn:
            # Optional: check whether userid exists first
            user = conn.execute(
                text("SELECT userid FROM users WHERE userid = :userid"),
                {"userid": payload.userid}
            ).fetchone()

            if not user:
                raise HTTPException(status_code=400, detail="Invalid userid")

            # Check if device already exists
            existing_device = conn.execute(
                text("SELECT deviceid FROM devices WHERE deviceid = :deviceid"),
                {"deviceid": payload.deviceid}
            ).fetchone()

            if existing_device:
                return {
                    "message": "Device already registered",
                    "deviceid": payload.deviceid
                }

            conn.execute(
                text("""
                    INSERT INTO devices (deviceid, userid, device_name, device_token)
                    VALUES (:deviceid, :userid, :device_name, :device_token)
                """),
                {
                    "deviceid": payload.deviceid,
                    "userid": payload.userid,
                    "device_name": payload.device_name,
                    "device_token": payload.device_token
                }
            )

        return {
            "message": "Device registered successfully",
            "deviceid": payload.deviceid
        }

    except IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.post("/searches")
def create_search(
    search: SearchCreate,
    x_api_key: str | None = Header(default=None)
):
    require_api_key(x_api_key)

    searchid = "S" + uuid.uuid4().hex[:14]

    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO searches (searchid, deviceid, query_text, url)
                    VALUES (:searchid, :deviceid, :query_text, :url)
                """),
                {
                    "searchid": searchid,
                    "deviceid": search.deviceid,
                    "query_text": search.query_text,
                    "url": search.url
                }
            )

        return {
            "message": "Search stored successfully",
            "searchid": searchid
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))