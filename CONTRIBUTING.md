# Contributing to IncidentFlow

Thank you for your interest in contributing to **IncidentFlow**! This document provides guidelines for contributing to this project in accordance with modern DevOps and SDLC best practices.

---

## 🧭 SDLC Workflow & Branching Strategy

We follow the **Git Feature-Branch Workflow**:
1. `main` is our production-ready branch. All commits here must pass automated CI pipelines.
2. Branch naming conventions:
   * `feat/<feature-name>`: New capabilities (e.g., `feat/slack-webhook-alert`)
   * `fix/<bug-name>`: Bug fixes (e.g., `fix/sqlite-connection-leak`)
   * `docs/<topic>`: Documentation updates
   * `test/<scope>`: Adding or improving tests

---

## 🛠️ Development Setup

1. **Clone & Virtual Environment:**
   ```bash
   git clone <repo-url>
   cd project-8-incident-management
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Environment Configuration:**
   ```bash
   cp .env.example .env
   ```
3. **Database Seeding:**
   ```bash
   python seed_data.py
   ```

---

## 🧪 Testing & Quality Assurance

Before submitting any Pull Request:
1. Ensure all unit and integration tests pass:
   ```bash
   pytest -v
   ```
2. Check formatting and linter standards against `.editorconfig`.
3. Verify the Docker build succeeds locally:
   ```bash
   docker build -t incidentflow:local .
   ```

---

## 📦 Pull Request Checklist

- [ ] Code adheres to PEP 8 / `.editorconfig` formatting rules.
- [ ] New REST API endpoints include corresponding tests in `tests/test_api.py`.
- [ ] No hardcoded passwords, tokens, or environment-specific paths.
- [ ] Meaningful commit messages following conventional commits (`feat:`, `fix:`, `chore:`, `docs:`).
