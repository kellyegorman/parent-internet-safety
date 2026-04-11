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
from fastapi.middleware.cors import CORSMiddleware
import uuid

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specific frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str = Field(..., min_length=8, max_length=72)

class DeviceCreate(BaseModel):
    userid: str = Field(..., max_length=15)
    device_name: str = Field(..., max_length=100)

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    userid: str

class SearchCreate(BaseModel):
    deviceid: str
    query_text: str
    url: str | None = None

class AlertCreate(BaseModel):
    deviceid: str
    categoryid: str
    severity: str
    domain: str | None = None
    reason_code: str | None = None

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
    hashed_password = pwd_context.hash(user.password)

    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT userid
                FROM users
                ORDER BY CAST(SUBSTRING(userid, 2) AS UNSIGNED) DESC
                LIMIT 1
            """)).fetchone()

            if result:
                last_num = int(result[0][1:])
                new_userid = f"u{last_num + 1}"
            else:
                new_userid = "u1"

            conn.execute(
                text("""
                    INSERT INTO users (userid, username, email, password_hash)
                    VALUES (:userid, :username, :email, :password_hash)
                """),
                {
                    "userid": new_userid,
                    "username": user.username,
                    "email": user.email,
                    "password_hash": hashed_password
                }
            )

        return {"message": "User created", "userid": new_userid}

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/users")
def get_users():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT userid, username, email FROM users")).fetchall()
    return {"users": [dict(r._mapping) for r in rows]}

@app.get("/userid")
def get_userid(email: str, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT userid
                    FROM users
                    WHERE email = :email
                    LIMIT 1
                """),
                {"email": email}
            ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        return {"userid": row[0]}

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        return {"access_token": token, "token_type": "bearer", "userid": userid}

    except HTTPException:
        raise
    except SQLAlchemyError:
        # Don't leak DB details to client
        raise HTTPException(status_code=500, detail="Database error")
    
@app.post("/devices")
def add_device(payload: DeviceCreate):
    try:
        with engine.begin() as conn:
            # Check if user exists
            user = conn.execute(
                text("SELECT userid FROM users WHERE userid = :userid"),
                {"userid": payload.userid}
            ).fetchone()

            if not user:
                raise HTTPException(status_code=400, detail="Invalid userid")

            # Generate new deviceid (d1, d2, d3...)
            result = conn.execute(
                text("""
                    SELECT deviceid
                    FROM devices
                    ORDER BY CAST(SUBSTRING(deviceid, 2) AS UNSIGNED) DESC
                    LIMIT 1
                """)
            ).fetchone()

            if result:
                last_num = int(result[0][1:])
                new_deviceid = f"d{last_num + 1}"
            else:
                new_deviceid = "d1"

            # Insert new device
            conn.execute(
                text("""
                    INSERT INTO devices (deviceid, userid, device_name)
                    VALUES (:deviceid, :userid, :device_name)
                """),
                {
                    "deviceid": new_deviceid,
                    "userid": payload.userid,
                    "device_name": payload.device_name
                }
            )

        return {
            "message": "Device registered successfully",
            "deviceid": new_deviceid
        }

    except IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
@app.get("/users/{userid}/devices")
def get_user_devices(
    userid: str,
    x_api_key: str | None = Header(default=None)
):
    require_api_key(x_api_key)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT deviceid, device_name, paired_at
                FROM devices
                WHERE userid = :userid
            """),
            {"userid": userid}
        ).mappings().all()

    return [dict(row) for row in rows]

@app.post("/searches")
def create_search(
    search: SearchCreate,
    x_api_key: str | None = Header(default=None)
):
    require_api_key(x_api_key)

    try:
        with engine.begin() as conn:
            result = conn.execute(
                    text("""
                        SELECT searchid
                        FROM searches
                        ORDER BY CAST(SUBSTRING(searchid, 2) AS UNSIGNED) DESC
                        LIMIT 1
                    """)
                ).fetchone()

            if result:
                last_num = int(result[0][1:])
                searchid = f"s{last_num + 1}"
            else:
                searchid = "s1"

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
    
@app.get("/users/{userid}/searches")
def get_user_searches(
    userid: str,
    x_api_key: str | None = Header(default=None)
):
    require_api_key(x_api_key)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT s.searchid, s.deviceid, s.query_text, s.url, s.searched_at
                FROM searches s
                JOIN devices d ON s.deviceid = d.deviceid
                WHERE d.userid = :userid
                ORDER BY s.searched_at DESC
            """),
            {"userid": userid}
        ).mappings().all()

    return [dict(row) for row in rows]

@app.post("/alerts")
def create_alert(payload: AlertCreate):
    try: 
        with engine.begin() as conn:
            result = conn.execute(
                    text("""
                        SELECT alertid
                        FROM alerts
                        ORDER BY CAST(SUBSTRING(alertid, 2) AS UNSIGNED) DESC
                        LIMIT 1
                    """)
                ).fetchone()

            if result:
                last_num = int(result[0][1:])
                alertid = f"a{last_num + 1}"
            else:
                alertid = "a1"

            conn.execute(
                text("""
                    INSERT INTO alerts (alertid, deviceid, categoryid, severity, domain, reason_code)
                    VALUES (:alertid, :deviceid, :categoryid, :severity, :domain, :reason_code)
                """),
                {
                    "alertid": alertid,
                    "deviceid": payload.deviceid,
                    "categoryid": payload.categoryid,
                    "severity": payload.severity,
                    "domain": payload.domain,
                    "reason_code": payload.reason_code
                }
            )
        return {
            "message": "Alert created",
            "alertid": alertid
        }
    
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/users/{userid}/alerts")
def get_user_alerts(
    userid: str,
    x_api_key: str | None = Header(default=None)
):
    require_api_key(x_api_key)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT a.alertid, a.deviceid, a.categoryid, a.severity,
                       a.domain, a.reason_code, a.created_at
                FROM alerts a
                JOIN devices d ON a.deviceid = d.deviceid
                WHERE d.userid = :userid
                ORDER BY a.created_at DESC
            """),
            {"userid": userid}
        ).mappings().all()

    return [dict(row) for row in rows]