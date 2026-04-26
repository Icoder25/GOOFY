# Goofy Backend

FastAPI backend services for the Goofy voice browser assistant.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run development server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

- `GET /` - Service info
- `GET /api/v1/health` - Health check
- `POST /api/v1/commands/parse` - Parse voice command (Phase 2)
- `POST /api/v1/commands/execute` - Execute command (Phase 3+)

## Testing

```bash
pytest tests/ -v
```

## Code Quality

```bash
# Linting
ruff check app/

# Formatting
black app/

# Format check
black --check app/
```
