# Tooling

## Core Runtime Requirements
- **Python 3.10+**: Backend runtime for FastAPI application
- **Node.js**: Frontend runtime for React/TypeScript application  
- **Docker & Docker Compose**: Primary containerization and orchestration platform

## Package Managers
- **uv**: Modern Python package manager with lockfile support (`uv.lock`)
  - Faster than pip, handles virtual environments automatically
  - Used for backend dependency management
- **npm**: Node.js package manager for frontend dependencies
  - Manages TypeScript, React, and build tool dependencies

## Backend Development Stack

### Core Framework & Database
- **FastAPI**: Modern Python web framework with automatic OpenAPI generation
- **SQLModel**: SQLAlchemy-based ORM with Pydantic integration for type safety
- **PostgreSQL 12**: Primary database with health checks
- **Alembic**: Database migration tool for schema changes
- **Pydantic**: Data validation and settings management

### Testing & Quality Tools
- **pytest**: Testing framework with coverage measurement
- **coverage**: Code coverage reporting with HTML output
- **mypy**: Static type checking with strict mode enabled
- **ruff**: Fast Python linter and formatter (replaces flake8, black, isort)
  - Configured in `pyproject.toml` with comprehensive rule sets

### Development Scripts
- `./backend/scripts/test.sh`: Run pytest with coverage reporting
- `./backend/scripts/lint.sh`: MyPy type checking + Ruff linting/formatting
- `./backend/scripts/format.sh`: Code formatting with Ruff

## Frontend Development Stack

### Core Framework & Libraries  
- **React 18**: Modern UI library with hooks
- **TypeScript**: Type-safe JavaScript with strict configuration
- **Vite**: Fast build tool and development server
- **TanStack Router 1.19.1**: File-based routing system
- **TanStack Query**: Server state management and caching
- **Chakra UI 3.8.0**: Component library with built-in dark mode support

### Code Quality & Testing
- **Biome 1.6.1**: Unified linter, formatter, and import organizer
  - Replaces ESLint + Prettier with single tool
  - Configured in `biome.json` with custom rules
- **Playwright**: End-to-end testing framework with browser automation
- **@hey-api/openapi-ts**: Auto-generates TypeScript client from backend OpenAPI spec

### Development Commands
- `npm run dev`: Start Vite development server (port 5173)
- `npm run build`: TypeScript compilation + Vite production build
- `npm run lint`: Biome linting with auto-fix
- `npm run generate-client`: Generate API client from OpenAPI spec
- `npx playwright test`: Run E2E tests

## Infrastructure & DevOps Tools

### Containerization
- **Docker**: Container runtime for service isolation
- **Docker Compose**: Multi-service orchestration with development overrides
  - `docker-compose.yml`: Production configuration
  - `docker-compose.override.yml`: Development-specific settings
  - File watching with automatic rebuilds (`docker compose watch`)

### Supporting Services
- **Traefik 3.0**: Reverse proxy with automatic service discovery
  - Routes traffic based on subdomains in production
  - Development dashboard at port 8090
- **PostgreSQL**: Database service with health checks
- **Adminer**: Web-based database administration UI (port 8080)
- **MailCatcher**: Email testing service for development (port 1080)

### Development Environment URLs
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Database Admin: http://localhost:8080  
- Traefik Dashboard: http://localhost:8090
- Email Testing: http://localhost:1080

## Code Quality Enforcement

### Pre-commit Hooks
- **pre-commit**: Automated code quality checks before Git commits
- Configured in `.pre-commit-config.yaml` with:
  - File size and format validation
  - TOML/YAML syntax checking
  - Python: Ruff linting and formatting
  - Trailing whitespace removal
  - End-of-file fixing

### Installation & Setup
```bash
# Install pre-commit hooks
uv run pre-commit install

# Run manually on all files  
uv run pre-commit run --all-files
```

## Development Workflow Options

### Full Stack Development (Recommended)
```bash
# Start entire stack with live reload
docker compose watch
```

### Individual Service Development
```bash
# Backend only (requires database running)
cd backend
fastapi dev app/main.py

# Frontend only (requires backend API)
cd frontend
npm run dev

# Stop specific services
docker compose stop frontend
docker compose stop backend
```

## Tool Categories Summary

### **Runtime & Language**
- Python 3.10+, Node.js, Docker

### **Package Management**  
- uv (Python), npm (JavaScript)

### **Backend Development**
- FastAPI, SQLModel, PostgreSQL, Alembic, pytest, mypy, ruff

### **Frontend Development**
- React, TypeScript, Vite, TanStack Router/Query, Chakra UI, Biome, Playwright

### **Infrastructure**
- Docker Compose, Traefik, Adminer, MailCatcher

### **Code Quality**
- Pre-commit hooks, automated linting/formatting, type checking
