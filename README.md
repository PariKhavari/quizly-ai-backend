# Quizly Backend (Django REST Framework)

Quizly turns YouTube videos into interactive quizzes using an AI pipeline:

1. Download YouTube audio (yt-dlp)
2. Transcribe audio (OpenAI Whisper)
3. Generate a 10-question quiz (Google Gemini)
4. Store quizzes and questions in the database
5. Let users play quizzes via attempts (save answers, resume, finish, results)

This repository contains the backend only (frontend is separate / not connected yet).

---

## Tech Stack

- Python (venv)
- Django + Django REST Framework
- JWT auth via HTTP-only cookies (SimpleJWT)
- Token blacklisting on logout
- yt-dlp (+ optional JS runtime support)
- Whisper (torch)
- Gemini API (google-genai)
- SQLite (default for dev)

---

## Features

### Authentication

- Register a user (`POST /api/register/`)
- Login (`POST /api/login/`)
  - sets `access_token` and `refresh_token` in HTTP-only cookies
- Refresh access token (`POST /api/token/refresh/`)
- Logout (`POST /api/logout/`)
  - invalidates refresh token (blacklist) and clears cookies

### Quiz Management

- Create quiz from YouTube URL (`POST /api/createQuiz/`)
- List user quizzes (`GET /api/quizzes/`)
- Quiz detail (`GET /api/quizzes/<quiz_id>/`)
- Update title/description (`PATCH /api/quizzes/<quiz_id>/`)
- Delete quiz (`DELETE /api/quizzes/<quiz_id>/`)

Permissions:

- All quiz endpoints require authentication
- Users can only access their own quizzes (returns 403 on forbidden access)

### Quiz Gameplay / Attempts (User Stories 8–9)

- Start or resume attempt (`POST /api/quizzes/<quiz_id>/start/`)
  - `{"new": true}` forces a fresh attempt
- Attempt detail (`GET /api/attempts/<attempt_id>/`)
- Save/update an answer (`PATCH /api/attempts/<attempt_id>/answer/`)
- Finish attempt (`POST /api/attempts/<attempt_id>/finish/`)
- Result / stats (`GET /api/attempts/<attempt_id>/result/?details=true`)

---

## Local Setup (Windows)

### 1) Create and activate venv

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2) Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3) Environment variables

Create a `.env` file in the project root:

```env
DJANGO_SECRET_KEY=your-secret-key
GEMINI_API_KEY=your-gemini-key
```

> Important: `.env` must NOT be committed.

### 4) Database migrations

```bash
python manage.py migrate
```

### 5) Create a superuser (admin panel)

```bash
python manage.py createsuperuser
```

### 6) Run the server

```bash
python manage.py runserver
```

Admin panel:

- http://127.0.0.1:8000/admin/

---

## Required External Tools

### FFmpeg

FFmpeg must be installed and available in PATH.

Windows (winget):

```bash
winget install --id Gyan.FFmpeg -e --source winget
```

### yt-dlp JS runtime warning (optional)

yt-dlp may warn about missing JS runtime for YouTube extraction.
This can reduce available formats, but downloads often still work.

---

## Quick API Tests (curl)

Open two terminals:

- Terminal A: `python manage.py runserver`
- Terminal B: run curl commands

### Register

```bash
curl -i -X POST http://127.0.0.1:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"testuser\",\"email\":\"testuser@example.com\",\"password\":\"Testpass123!\",\"confirmed_password\":\"Testpass123!\"}"
```

### Login (store cookies)

```bash
curl -i -c cookies.txt -X POST http://127.0.0.1:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"testuser\",\"password\":\"Testpass123!\"}"
```

### Refresh access token (updates cookies.txt)

```bash
curl -i -b cookies.txt -c cookies.txt -X POST http://127.0.0.1:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d "{}"
```

### Create Quiz

```bash
curl -i -b cookies.txt -X POST http://127.0.0.1:8000/api/createQuiz/ \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://www.youtube.com/watch?v=dQw4w9WgXcQ\"}"
```

### List Quizzes

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/api/quizzes/
```

### Start Attempt (force new)

```bash
curl -i -b cookies.txt -X POST http://127.0.0.1:8000/api/quizzes/13/start/ \
  -H "Content-Type: application/json" \
  -d "{\"new\": true}"
```

### Logout

```bash
curl -i -b cookies.txt -X POST http://127.0.0.1:8000/api/logout/ \
  -H "Content-Type: application/json" \
  -d "{}"
```

After logout, refresh should fail:

```bash
curl -i -b cookies.txt -X POST http://127.0.0.1:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d "{}"
```

---

## Project Structure

- `auth_app/`  
  Authentication endpoints, cookie-based JWT handling, logout blacklist logic.
- `quizly_app/`
  - `api/` DRF views, serializers, URLs
  - `models.py` Quiz, Question, QuizAttempt, AttemptAnswer
  - `services/` YouTube download, transcription, Gemini generation, orchestration

### Notes about `services/generation.py` and `services/pipeline.py`

These modules are intentionally kept as documented placeholders for future refactoring.
The active orchestration currently lives in `quiz_creation.py` and related service modules.

---

## Common Issues

### 401 "token expired"

Run refresh:

```bash
curl -i -b cookies.txt -c cookies.txt -X POST http://127.0.0.1:8000/api/token/refresh/ -H "Content-Type: application/json" -d "{}"
```

### Browser 400 JSON parse error

Make sure the request body is valid JSON and uses double quotes:

```json
{ "url": "https://www.youtube.com/watch?v=..." }
```

### Whisper: "FP16 not supported on CPU"

This is a warning, not a failure. Whisper uses FP32 on CPU.
