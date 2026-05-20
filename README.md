# LMBot Backend

AI-powered customer service backend for Lanemark, built with FastAPI and LangChain.
API can be accessed on https://lmbot-api.onrender.com

---

# Running Locally:

## Prerequisites

Make sure the following are installed on your machine:

- **Python 3.11+** — https://www.python.org/downloads/
- **PostgreSQL** — https://www.postgresql.org/download/

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <repository-url>
cd lmbot-backend
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the database

Open PostgreSQL and run:

```sql
CREATE DATABASE lmbot_db;
```

### 5. Configure environment variables

Create a `.env` file in the root of the project with the following contents:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:<your-password>@localhost:5432/lmbot_db
DATABASE_ECHO=True
DB_USER=postgres
DB_PASSWORD=<your-password>
DB_HOST=localhost
DB_PORT=5432
DB_NAME=lmbot_db

# OpenAI
OPENAI_API_KEY=<your-openai-api-key>
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Application
APP_NAME=Lanemark Bot API
DEBUG=True

# Security
SECRET_KEY=any-random-secret-string

# RAG Settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_DOCUMENTS=5
SIMILARITY_THRESHOLD=0.3
SEMANTIC_CHUNKING_BREAKPOINT_THRESHOLD_TYPE=percentile
SEMANTIC_CHUNKING_BREAKPOINT_THRESHOLD=95.0
SEMANTIC_CHUNKING_MIN_CHUNK_SIZE=100

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

Replace `<your-password>` with your PostgreSQL password and `<your-openai-api-key>` with a valid OpenAI API key.

### 6. Run the application

```bash
python main.py
```

The API will be available at: **http://127.0.0.1:8000**

---

## API Documentation

Once the server is running, visit:

- **Swagger UI:** http://127.0.0.1:8000/docs

---

## API Endpoints

| Prefix | Description |
|--------|-------------|
| `/api/v1/chatbot` | Chat with the AI assistant |
| `/api/v1/documents` | Upload and manage knowledge base documents |
| `/api/v1/triage` | Classify and route customer queries |

---
