# Extension Guide

This guide explains how to add new domain applications to the scaffold platform.

## 1. Create a Module Package

1. Copy `scaffold/apps/template` to `scaffold/apps/<your_app>`.
2. Rename the blueprint and URL prefix to match the new domain.
3. Add the module path to `SCAFFOLD_APP_MODULES` (comma-separated list).

## 2. Register Blueprints and Services

- Expose a `register(app)` function that:
  - Registers blueprints.
  - Binds CLI commands.
  - Sets up signal handlers or background jobs.
- Optionally define `init_app(app)` for additional bootstrapping.

## 3. Models and Migrations

- Create models under `scaffold/apps/<your_app>/models.py` or a package.
- Import the shared SQLAlchemy `db` instance from `scaffold.extensions`.
- Run `poetry run flask --app scaffold:create_app db migrate -m "Add <your_app> models"`.
- Add seed data scripts if required.

## 4. Templates and Static Assets

- Place templates under `scaffold/apps/<your_app>/templates/<your_app>/`.
- Inherit from the shared base template (`layout.html`) to get Bootstrap dark mode and navigation.
- Add static files under `scaffold/apps/<your_app>/static/` and ensure they integrate with the asset pipeline.

## 5. Forms and Services

- Reuse shared form validators or create new ones in your module.
- Encapsulate domain logic in services so it can be unit tested independently.

## 6. Documentation and Tests

- Document domain-specific behaviour in `docs/` (e.g., `docs/<your_app>_guide.md`).
- Add unit/integration tests under `tests/<your_app>/`.
- Update `docs/architecture.md` and `docs/history.md` to reflect the new module.

## 7. Review Checklist

- [ ] Routes appear in navigation and respect authorisation.
- [ ] MFA and session security flows work for the new module.
- [ ] Database migrations succeed on PostgreSQL and MariaDB.
- [ ] Documentation updated and linked from the main README.
