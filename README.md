# Insighta Labs+ — Backend

Secure REST API for the Insighta demographic intelligence platform.

## System Architecture

```
insighta-backend/
├── app/
│   ├── routers/        # HTTP route handlers only
│   ├── services/       # Business logic (profiles, github, external APIs)
│   ├── core/           # Shared utilities (tokens, users, countries)
│   ├── middleware/      # Logging, rate limiting
│   ├── dependencies/   # FastAPI dependency injection
│   └── models.py       # SQLAlchemy ORM models
├── scripts/            # Admin promotion script
└── tests/
```

Three tables: `profiles`, `users`, `refresh_tokens`.

## Authentication Flow

### Browser (Web Portal)
1. User clicks "Continue with GitHub"
2. Backend redirects to `GET /auth/github` → GitHub OAuth page
3. GitHub redirects to `GET /auth/github/callback`
4. Backend exchanges code, creates/updates user, issues token pair
5. Backend sets HTTP-only cookies (`access_token`, `refresh_token`)
6. Redirects to `http://localhost:3000/auth/callback`

### CLI (PKCE Flow)
1. CLI generates `state`, `code_verifier`, `code_challenge`
2. CLI starts local HTTP server on `localhost:9876`
3. CLI calls `GET /auth/github?state=...&code_challenge=...&code_verifier=...&redirect_uri=http://localhost:9876/callback`
4. Backend stores `code_verifier` keyed by `state`
5. After GitHub auth, backend detects `cli_redirect_uri`, redirects to CLI server with tokens in query params
6. CLI reads tokens, stores in `~/.insighta/credentials.json`

## Token Handling

| Token | Type | Expiry | Storage |
|-------|------|--------|---------|
| Access token | JWT (HS256) | 3 minutes | Browser cookie / CLI file |
| Refresh token | Opaque (SHA-256 hashed in DB) | 5 minutes | Browser cookie / CLI file |

- Refresh tokens are single-use — revoked immediately on use, new pair issued
- Access tokens carry `sub` (user ID), `role`, `username`
- Expired access token → auto-refresh attempted → re-login if refresh also expired

## Role Enforcement

Two roles: `admin` and `analyst` (default).

| Action | Admin | Analyst |
|--------|-------|---------|
| List profiles | ✓ | ✓ |
| Search profiles | ✓ | ✓ |
| Get profile | ✓ | ✓ |
| Export CSV | ✓ | ✓ |
| Create profile | ✓ | ✗ |
| Delete profile | ✓ | ✗ |
| Promote users | ✓ | ✗ |

Enforced via FastAPI dependency injection:
- `CurrentUser` — any authenticated user
- `AdminUser` — admin role required

Disabled accounts (`is_active = false`) receive `403` on all requests.

## Natural Language Parsing

Rule-based only. No LLMs.

### Supported keywords

**Gender:** male, males, man, men, boy, boys, female, females, woman, women, girl, girls

**Age groups:** child, children, kid, kids, teenager, teenagers, teen, teens, adult, adults, senior, seniors, elderly, old

**Age ranges:**
- `young` / `youth` → min_age=16, max_age=24
- `above N` / `over N` / `older than N` → min_age=N
- `below N` / `under N` / `younger than N` → max_age=N
- `between N and M` → min_age=N, max_age=M

**Countries:** Full country names matched against a dictionary (longest match wins to avoid "niger" matching inside "nigeria")

### Examples

| Query | Filters |
|-------|---------|
| `young males from nigeria` | gender=male, min_age=16, max_age=24, country_id=NG |
| `adult females above 30` | gender=female, age_group=adult, min_age=30 |
| `people from guinea-bissau` | country_id=GW |
| `seniors under 80` | age_group=senior, max_age=80 |

### Limitations
- No stemming — "male" matches but "masculine" does not
- Country matching is name-based only, not ISO code
- Queries with no recognizable tokens return `400 Unable to interpret query`
- No negation support ("not from nigeria")
- No OR logic ("males or females")

## API Reference

All `/api/*` endpoints require:
- `Authorization: Bearer <access_token>`
- `X-API-Version: 1`

### Auth
| Method | Path | Auth |
|--------|------|------|
| GET | `/auth/github` | None |
| GET | `/auth/github/callback` | None |
| POST | `/auth/refresh` | None |
| POST | `/auth/logout` | None |
| GET | `/auth/me` | Any |

### Profiles
| Method | Path | Role |
|--------|------|------|
| GET | `/api/profiles` | Any |
| POST | `/api/profiles` | Admin |
| GET | `/api/profiles/search` | Any |
| GET | `/api/profiles/export` | Any |
| GET | `/api/profiles/{id}` | Any |
| DELETE | `/api/profiles/{id}` | Admin |

### Admin
| Method | Path | Role |
|--------|------|------|
| PATCH | `/api/admin/users/{id}/promote` | Admin |

## Rate Limits

| Scope | Limit |
|-------|-------|
| `/auth/*` | 10 req/min |
| All other endpoints | 60 req/min per user |

## Setup

```bash
git clone https://github.com/muizzyranking/insighta-backend
cd insighta-backend
uv sync
cp .env.example .env  # fill in values
uv run python -m app.seed
uv run fastapi dev app/app.py
```

### Environment variables

```env
SECRET_KEY=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback
DATABASE_URL=sqlite+aiosqlite:///./insighta.db
APP_ENV=development
```

### Make yourself admin

```bash
uv run python scripts/make_admin.py your-github-username
```

## Running Tests

```bash
uv run pytest tests/ -v
```
