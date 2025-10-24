# Migrations

This directory will contain Alembic migration scripts for the unified scaffold metadata. Initialise the environment with:

```bash
poetry run flask --app scaffold:create_app db init
```

> Note: the command above will populate this folder with Alembic configuration files. Commit those files after reconciling the schemas from `bia_app` and `csa_app`.
