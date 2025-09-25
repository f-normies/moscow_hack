# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Plan & Review

### Before starting work
- Always in plan mode to make a plan
- After getting the plan, make sure you Write the plan to .claude/tasks/TASK_NAME.md throughly and with production-ready plan
- The plan should be detailed implementation plan and the reasoning behind it, as well as tasks broken down.
- If the task require external knowledge or certain package, also research to get latest knowledge (Use Task tool and context7 mcp for research).
- Each task equals atomic feature, fix or chore, don't overplan it.
- Once you write the plan, firstly ask me to review it. Do not continue until I approve the plan.

### While implementing
- You should update the plan as you work.
- After you complete tasks in the plan, you should update and append detailed descriptions of the changes you made, so following tasks can be easily hand over to other engineers.

## Architecture Overview

This is a full-stack web application template with:
- Backend: FastAPI with SQLModel/Pydantic for data validation and PostgreSQL as the database
- Frontend: React with TypeScript, TanStack Router, TanStack Query, and Chakra UI
- Containerization: Docker Compose for both development and production environments
- Testing: Pytest for backend testing, Playwright for frontend E2E testing
- Code Quality: Pre-commit hooks with Ruff (Python) and Biome (TypeScript)

## Development Environment

### Docker Compose Development
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Database admin: http://localhost:8080
- Traefik dashboard: http://localhost:8090

### Environment Configuration
- Main config: `.env` file in project root
- Development overrides: `docker-compose.override.yml`
- Production deployment: `docker-compose.yml` only

## Code Quality Standards

- When creating new feature always look at the "surrounding" code to mimic style of writing and get better context
- Research backend/README.md when working on the backend to retrieve better context
- Research frontend/README.md when working on the frontend to retrieve better context

### Database Migrations
- Tool: Alembic for database schema migrations
- Location: `backend/app/alembic/versions/`
- Generation: `docker compose exec backend alembic revision --autogenerate -m "description"`
- Application: Automatic on container startup via `backend_pre_start.py`

## Git Workflow Guidelines

### GitHub Flow Process
This project follows GitHub Flow for all development work:

1. Always start from main: Create feature branches from the latest main branch
2. Descriptive branch names: Use prefixes like `feature/`, `fix/`, `chore/`
3. Pull Request required: All changes must go through PR review process
4. Main is deployable: The main branch should always be in a deployable state

### Branch Naming Convention
```bash
feature/user-authentication    # New features
fix/database-connection       # Bug fixes
chore/update-dependencies     # Maintenance tasks
docs/api-documentation        # Documentation updates
```

### Commit Messages
Follow Conventional Commits specification:
- `feat:` - New features
- `fix:` - Bug fixes
- `chore:` - Maintenance tasks
- `docs:` - Documentation changes
- `test:` - Test additions or modifications
- `refactor:` - Code refactoring without functionality changes

### Pre-commit Workflow
Before each commit, ensure:
1. Pre-commit hooks pass (Ruff for Python, Biome for TypeScript)
2. All tests pass locally: `./scripts/test.sh`
3. No linting errors in your changes
4. Code follows existing patterns and conventions
