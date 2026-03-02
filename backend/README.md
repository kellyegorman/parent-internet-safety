# README for Senior Capstone Backend

## Overview
This is the FastAPI backend for our Senior Capstone project.

The backend:
- Provides REST API endpoints
- Connects to a MySQL database (Railway-hosted)
- Handles user creation and data storage
- Is deployed on Railway with automatic GitHub deployment

The database is not publicly exposed, only the API service can access it.

## Live Deployment
Base URL:
```
https://senior-project-production-4c90.up.railway.app
```

Swagger Docs: 
```
https://senior-project-production-4c90.up.railway.app/docs
```

## Architecture

Frontend
   ↓
Railway Backend (Public API)
   ↓
Railway MySQL (Private Network)

- Backend is publicly accessible
- Database private within Railway network
- Environment variables managed by Railway

## Local Setup
1. Clone Repo
``` bash
git clone https://github.com/YOUR_REPO
cd senior-project/backend
```
2. Create virtual environment
``` bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
```
3. Install dependencies
``` bash
pip install -r requirements.txt
```
4. Create .env file
``` env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:PORT/DBNAME
API_KEY=your_api_key_here
```
do not commit .env file

5. Run locally
``` bash
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:PORT/DBNAME
API_KEY=your_api_key_here
```

Then open:
```
http://127.0.0.1:8000/docs
```

## API Authentication
Some endpoints require an API key.

When making requests, include the following header:
```http
x-api-key: YOUR_API_KEY
```

## Available Endpoints
| Method | Endpoint     | Description          |
|--------|-------------|----------------------|
| GET    | /health     | Health check         |
| GET    | /db-check   | Database test        |
| GET    | /tables     | List tables          |
| POST   | /users      | Create new user      |
| GET    | /users      | Get users            |

## Database
Database is hosted on Railway (MySQL)

Connection handled using:
- SQLAlchemy
- PyMySQL Driver

Environment variable:
```
DATABASE_URL
```

## Deployment
Deployment automatic via Github

Whenever changes are pushed to main:
``` bash
git push origin main
```
Railway redeploys automatically

## Important Notes
- .env only used locally
- Railway uses service variables for production
- Do not commit API key/Database URL
- Database not publicly accessible

## Team Workflow
- Backend runs live on Railway
- Frontend should use deployed base URL
- Test endpoints via /docs before frontend integration
- Make local changes → test → push → automatic deploy

## Tech Stack
- Python 3.11+
- FastAPI
- SQLAlchemy
- PyMySQL
- Railway
- MySQL

## Capstone Context
This backend is part of a larger system designed to support:
- User/device management
- Alert processing
- Content categorization
- Secure API-based communication

The architecture separates:
- Compute layer (API)
- Data layer (MySQL)
- Frontend layer

## Status
Backend successfully deployed and connected to MySQL database! More endpoints for further actions will be added



