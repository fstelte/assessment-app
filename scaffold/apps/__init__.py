"""Application module namespace.

Modules placed in this package are discovered by the registry and must expose
one of the following entry points:

- `register(app: Flask)` function that binds blueprints and services.
- `blueprints` attribute containing a `Blueprint` or iterable of `Blueprint`s.
- `init_app(app: Flask)` for additional setup after registration.

See `scaffold.apps.template` for a starter layout when creating new domains.
"""
