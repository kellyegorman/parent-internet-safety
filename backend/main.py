import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import BaseModel, Field
import uuid
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# change to railway API key from eleanor
API_KEY      = os.getenv("railway_api")
JWT_SECRET   = os.getenv("JWT_SECRET")
JWT_ALG      = os.getenv("JWT_ALG", "HS256")
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "60"))
DATABASE_URL = os.getenv("DATABASE_URL")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET not set")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env")

engine       = create_engine(DATABASE_URL, pool_pre_ping=True)
pwd_context  = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(title="Capstone API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def require_api_key(x_api_key: str | None):

    if not API_KEY:
        # if API_KEY isn't set on Railway, skip check so writes still work
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

def get_current_userid(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> str:
    # Decode JWT and return userid. Used by dashboard read endpoints.
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALG])
        userid = payload.get("sub")
        if not userid:
            raise HTTPException(status_code=401, detail="Invalid token")
        return userid
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_access_token(*, sub: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRE_MIN)
    payload = {"sub": sub, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


class UserCreate(BaseModel):
    username: str
    email: str
    password: str = Field(..., min_length=8, max_length=72)

class DeviceCreate(BaseModel):
    deviceid: str     = Field(..., max_length=15)
    userid: str       = Field(..., max_length=15)
    device_name: str  = Field(..., max_length=100)
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

class AlertCreate(BaseModel):
    deviceid: str
    categoryid: str
    severity: str
    domain: str | None = None
    reason_code: str | None = None

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
        hashed  = pwd_context.hash(user.password)
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO users (userid, username, email, password_hash) VALUES (:userid, :username, :email, :password)"),
                {"userid": user_id, "username": user.username, "email": user.email, "password": hashed}
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

@app.get("/userid")
def get_userid(email: str, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT userid FROM users WHERE email = :email LIMIT 1"),
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
        raise HTTPException(status_code=500, detail="Database error")


@app.post("/devices")
def add_device(payload: DeviceCreate):
    try:
        with engine.begin() as conn:
            user = conn.execute(
                text("SELECT userid FROM users WHERE userid = :userid"),
                {"userid": payload.userid}
            ).fetchone()
            if not user:
                raise HTTPException(status_code=400, detail="Invalid userid")

            existing = conn.execute(
                text("SELECT deviceid FROM devices WHERE deviceid = :deviceid"),
                {"deviceid": payload.deviceid}
            ).fetchone()
            if existing:
                return {"message": "Device already registered", "deviceid": payload.deviceid}

            conn.execute(
                text("INSERT INTO devices (deviceid, userid, device_name, device_token) VALUES (:deviceid, :userid, :device_name, :device_token)"),
                {"deviceid": payload.deviceid, "userid": payload.userid,
                 "device_name": payload.device_name, "device_token": payload.device_token}
            )
        return {"message": "Device registered successfully", "deviceid": payload.deviceid}
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/users/{userid}/devices")
def get_user_devices(userid: str, current_user: str = Depends(get_current_userid)):
    if current_user != userid:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT deviceid, device_name, paired_at FROM devices WHERE userid = :userid"),
                {"userid": userid}
            ).fetchall()
        return {"devices": [dict(r._mapping) for r in rows]}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/searches")
def create_search(search: SearchCreate, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    searchid = "S" + uuid.uuid4().hex[:14]
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO searches (searchid, deviceid, query_text, url) VALUES (:searchid, :deviceid, :query_text, :url)"),
                {"searchid": searchid, "deviceid": search.deviceid,
                 "query_text": search.query_text, "url": search.url}
            )
        return {"message": "Search stored successfully", "searchid": searchid}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{userid}/searches")
def get_user_searches(userid: str, current_user: str = Depends(get_current_userid)):
    if current_user != userid:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT s.searchid, s.deviceid, s.query_text, s.url, s.searched_at,
                           COALESCE(s.flagged, FALSE) as flagged
                    FROM searches s
                    JOIN devices d ON s.deviceid = d.deviceid
                    WHERE d.userid = :userid
                    ORDER BY s.searched_at DESC
                    LIMIT 50
                """),
                {"userid": userid}
            ).fetchall()
        return {"searches": [dict(r._mapping) for r in rows]}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts")
def create_alert(alert: AlertCreate, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    alertid = "A" + uuid.uuid4().hex[:14]
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO alerts (alertid, deviceid, categoryid, severity, domain, reason_code) VALUES (:alertid, :deviceid, :categoryid, :severity, :domain, :reason_code)"),
                {"alertid": alertid, "deviceid": alert.deviceid, "categoryid": alert.categoryid,
                 "severity": alert.severity, "domain": alert.domain, "reason_code": alert.reason_code}
            )
        return {"message": "Alert created", "alertid": alertid}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{userid}/alerts")
def get_user_alerts(userid: str, current_user: str = Depends(get_current_userid)):
    if current_user != userid:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT a.alertid, a.severity, a.domain, a.reason_code, a.created_at,
                           ac.category_name, ac.categoryid
                    FROM alerts a
                    JOIN devices d ON a.deviceid = d.deviceid
                    LEFT JOIN alert_category ac ON a.categoryid = ac.categoryid
                    WHERE d.userid = :userid
                    ORDER BY a.created_at DESC
                    LIMIT 50
                """),
                {"userid": userid}
            ).fetchall()
        return {"alerts": [dict(r._mapping) for r in rows]}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/me")
def me(current_user: str = Depends(get_current_userid)):
    return {"userid": current_user}
