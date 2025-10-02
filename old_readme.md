# Web Fullstack Template

## Basic setup

1. Prerequisites:
    - Python 3.10+
    - [Node.js](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)
    - [Docker](https://docs.docker.com/engine/install/)
2. Install package managers and misc:
    - [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python
    - [npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) for TypeScript and React
    - [fnm](https://github.com/Schniz/fnm#installation) for Node version managing
3. Configure backend:

```bash
cd backend && uv sync
```

```bash
source .venv/bin/activate
```

4. Configure frontend:

```bash
cd frontend && fnm install
```

```bash
fnm use
```

```bash
npm install
```

5. Configure MinIO:

```bash
sudo nano /etc/hosts
```

```txt
127.0.0.1       minio
```

Note: Correctly proxying MinIO to localhost was a MASSIVE pain in the ass. Just use this to overcome the problems.

6. Read [backend/README.md](./backend/README.md) and [frontend/README.md](./frontend/README.md) for development guidelines!

Use these credentials to check services:

```
Backend Admin Login
  - Email: admin@webapp.com
  - Password: GYSgmXnhFR3p7-4x-2D21A

MinIO Storage Credentials

  Root Admin Access (Console)
  - Username: minio
  - Password: KaAsm5IXs--CrKeEFILGkA

  Application Service Access
  - Access Key: app-service-minio
  - Secret Key: 9f0jReES1fs8Bj_XoF7ViPAKB1k

```

## Technology Stack and Features

- ⚡ [**FastAPI**](https://fastapi.tiangolo.com) for the Python backend API.
    - 🧰 [SQLModel](https://sqlmodel.tiangolo.com) for the Python SQL database interactions (ORM).
    - 🔍 [Pydantic](https://docs.pydantic.dev), used by FastAPI, for the data validation and settings management.
    - 💾 [PostgreSQL](https://www.postgresql.org) as the SQL database.
- 🚀 [React](https://react.dev) for the frontend.
    - 💃 Using TypeScript, hooks, Vite, and other parts of a modern frontend stack.
    - 🎨 [Chakra UI](https://chakra-ui.com) for the frontend components.
    - 🤖 An automatically generated frontend client.
    - 🧪 [Playwright](https://playwright.dev) for End-to-End testing.
    - 🦇 Dark mode support.
- 🐋 [Docker Compose](https://www.docker.com) for development and production.
- 🔒 Secure password hashing by default.
- 🔑 JWT (JSON Web Token) authentication.
- 📫 Email based password recovery.
- ✅ Tests with [Pytest](https://pytest.org).
- 📞 [Traefik](https://traefik.io) as a reverse proxy / load balancer.
- 🚢 Deployment instructions using Docker Compose, including how to set up a frontend Traefik proxy to handle automatic HTTPS certificates.

## Backend Development

Backend docs: [backend/README.md](./backend/README.md).

## Frontend Development

Frontend docs: [frontend/README.md](./frontend/README.md).

## Deployment

Deployment docs: [deployment.md](./deployment.md).

## Development

General development docs: [development.md](./development.md).

This includes using Docker Compose, custom local domains, `.env` configurations, etc.
