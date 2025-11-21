"""Helpers for recording and pruning audit log events."""

from __future__ import annotations

import enum
import json
import logging
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from datetime import UTC, datetime, date, time, timedelta
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from flask import Flask, current_app, has_app_context, has_request_context, request
from flask_login import current_user
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError

from ..extensions import db


def _resolve_actor(provided_user: Any | None) -> tuple[int | None, str | None, str | None]:
    def _name_from_user(candidate: Any) -> str | None:
        full_name = getattr(candidate, "full_name", None)
        if isinstance(full_name, str) and full_name.strip():
            return full_name.strip()
        first = getattr(candidate, "first_name", None)
        last = getattr(candidate, "last_name", None)
        names = [name.strip() for name in (first, last) if isinstance(name, str) and name.strip()]
        if names:
            return " ".join(names)
        username = getattr(candidate, "username", None)
        if isinstance(username, str) and username.strip():
            return username.strip()
        return None

    subject = provided_user
    if subject is None and has_request_context():
        try:
            if current_user.is_authenticated:  # type: ignore[attr-defined]
                subject = current_user
        except Exception:  # pragma: no cover - defensive access
            subject = None

    if subject is not None:
        actor_id = getattr(subject, "id", None)
        actor_email = getattr(subject, "email", None)
        if isinstance(actor_email, str) and not actor_email.strip():
            actor_email = None
        actor_name = _name_from_user(subject)
        return actor_id, actor_email, actor_name

    return None, None, None


def _determine_ip(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    if not has_request_context():
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr


def _determine_user_agent(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    if not has_request_context():
        return None
    return request.headers.get("User-Agent")


def log_event(
    action: str,
    entity_type: str,
    *,
    entity_id: str | int | None = None,
    details: Mapping[str, Any] | None = None,
    user: Any | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
    flush: bool = True,
):
    """Persist an audit trail record, honouring configuration toggles."""

    if not action or not entity_type:
        raise ValueError("'action' and 'entity_type' are required")
    if not has_app_context():
        raise RuntimeError("log_event requires an active Flask application context")

    app = current_app
    if not app.config.get("AUDIT_LOG_ENABLED", True):
        return None

    from ..models import AuditLog  # local import to avoid circular dependency

    actor_id, actor_email, actor_name = _resolve_actor(user)
    resolved_ip = _determine_ip(ip_address)
    resolved_agent = _determine_user_agent(user_agent)

    payload_data = dict(details) if details is not None else None
    event_kwargs: dict[str, Any] = {
        "actor_id": actor_id,
        "actor_email": actor_email,
        "actor_name": actor_name,
        "actor_ip": resolved_ip,
        "actor_user_agent": resolved_agent,
        "event_type": action,
        "target_type": entity_type,
        "target_id": str(entity_id) if entity_id is not None else None,
        "payload": payload_data,
    }

    event = AuditLog(**event_kwargs)

    db.session.add(event)
    try:
        if flush:
            db.session.flush()
        logger = logging.getLogger("scaffold.audit")
        if logger.handlers:
            timestamp = event.created_at or datetime.now(UTC)
            log_payload = {
                "event": event.event_type,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "actor_id": event.actor_id,
                "actor_email": event.actor_email,
                "actor_ip": event.actor_ip,
                "timestamp": timestamp.isoformat(),
                "payload": event.payload,
            }
            logger.info(json.dumps(log_payload, ensure_ascii=False))
        if commit:
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
    return event


def prune_expired_events(retention_days: int | None = None) -> int:
    """Delete audit trail rows older than the configured retention window."""

    if not has_app_context():
        raise RuntimeError("prune_expired_events requires an active Flask application context")

    app = current_app
    if not app.config.get("AUDIT_LOG_ENABLED", True):
        return 0

    window_days = retention_days if retention_days is not None else int(app.config.get("AUDIT_LOG_RETENTION_DAYS", 0))
    if window_days <= 0:
        return 0

    cutoff = datetime.now(UTC) - timedelta(days=window_days)

    from ..models import AuditLog  # local import to avoid circular dependency

    delete_stmt = sa.delete(AuditLog).where(AuditLog.created_at < cutoff)
    try:
        result = db.session.execute(delete_stmt)
        db.session.commit()
    except (ProgrammingError, OperationalError) as exc:
        db.session.rollback()
        message = str(exc).lower()
        if "audit_logs" in message and "does not exist" in message:
            current_app.logger.debug("Audit log table missing; skipping prune until migrations run.")
            return 0
        raise
    return result.rowcount or 0


def enforce_audit_retention(
    *,
    retention_days: int | None = None,
    log_path: str | None = None,
) -> dict[str, int]:
    """Prune audit database rows and rotated log files exceeding the retention window."""

    if not has_app_context():
        raise RuntimeError("enforce_audit_retention requires an active Flask application context")

    app = current_app
    if not app.config.get("AUDIT_LOG_ENABLED", True):
        return {"db_deleted": 0, "files_deleted": 0}

    try:
        configured_retention = int(app.config.get("AUDIT_LOG_RETENTION_DAYS", 0))
    except (TypeError, ValueError):
        configured_retention = 0

    effective_retention = retention_days if retention_days is not None else configured_retention
    log_target = log_path or app.config.get("AUDIT_LOG_PATH")

    removed_rows = prune_expired_events(retention_days=effective_retention)
    removed_files = 0

    if (
        effective_retention is not None
        and effective_retention > 0
        and isinstance(log_target, str)
        and log_target.strip()
    ):
        try:
            primary_path = Path(log_target).expanduser()
            parent = primary_path.parent
            if parent.exists():
                cutoff = datetime.now(UTC) - timedelta(days=int(effective_retention))
                pattern = f"{primary_path.name}*"
                for candidate in parent.glob(pattern):
                    if candidate == primary_path:
                        continue
                    try:
                        stats = candidate.stat()
                    except FileNotFoundError:
                        continue
                    modified = datetime.fromtimestamp(stats.st_mtime, tz=UTC)
                    if modified < cutoff:
                        try:
                            candidate.unlink()
                            removed_files += 1
                        except FileNotFoundError:
                            continue
                        except OSError:
                            app.logger.warning(
                                "Failed to remove expired audit log file %s", candidate, exc_info=True
                            )
        except Exception:  # pragma: no cover - defensive logging
            app.logger.exception("Audit log file retention enforcement failed")

    return {"db_deleted": removed_rows, "files_deleted": removed_files}


def log_change_event(
    action: str,
    entity_type: str,
    *,
    entity_id: str | int | None = None,
    changes: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    user: Any | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
    flush: bool = True,
):
    details: dict[str, Any] = {}
    if metadata:
        details.update(dict(metadata))
    if changes:
        details.setdefault("changes", dict(changes))

    event_type = f"{entity_type}.{action}" if entity_type else action
    return log_event(
        action=event_type,
        entity_type=entity_type or "unknown",
        entity_id=entity_id,
        details=details,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        commit=commit,
        flush=flush,
    )


def log_login_event(
    status: str,
    *,
    user: Any | None = None,
    email: str | None = None,
    reason: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
    flush: bool = True,
):
    normalized_status = status.lower().strip() if status else "unknown"
    details: dict[str, Any] = {"status": normalized_status}
    if metadata:
        details.update(dict(metadata))
    if reason:
        details["reason"] = reason
    if email:
        details["email"] = email

    entity_id = getattr(user, "id", None) if user is not None else (email or None)

    return log_event(
        action=f"auth.login.{normalized_status}",
        entity_type="auth",
        entity_id=entity_id,
        details=details,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        commit=commit,
        flush=flush,
    )


_PENDING_EVENTS_KEY = "_scaffold_pending_audit_events"
_DEFAULT_OPERATIONS = frozenset({"insert", "update", "delete"})
_ALLOWED_OPERATIONS = {"insert", "update", "delete"}

_DEFAULT_AUTO_AUDIT_CONFIG: Mapping[str, Mapping[str, Any]] = MappingProxyType(
    {
        "scaffold.apps.identity.models.User": {
            "entity": "user",
            "fields": (
                "email",
                "status",
                "first_name",
                "last_name",
                "is_service_account",
                "locale_preference",
                "theme_preference",
            ),
            "identity_field": "id",
            "fallback_identity": ("email",),
        },
        "scaffold.apps.identity.models.Role": {
            "entity": "role",
            "fields": ("name", "description"),
            "identity_field": "id",
            "fallback_identity": ("name",),
        },
    }
)


@dataclass(frozen=True)
class ModelChangeSpec:
    model: type
    entity_type: str
    tracked_fields: tuple[str, ...]
    identity_attr: str = "id"
    identity_fallbacks: tuple[str, ...] = ()
    operations: frozenset[str] = field(default_factory=lambda: _DEFAULT_OPERATIONS)

    def resolve_identity(self, instance: Any) -> Any:
        value: Any = None
        if self.identity_attr:
            value = getattr(instance, self.identity_attr, None)
        if value in (None, ""):
            for fallback in self.identity_fallbacks:
                candidate = getattr(instance, fallback, None)
                if candidate not in (None, ""):
                    value = candidate
                    break
        return value


@dataclass
class PendingAuditChange:
    spec: ModelChangeSpec
    action: str
    entity_id: Any | None
    changes: Mapping[str, Any] | None
    metadata: Mapping[str, Any] | None
    instance_ref: Any | None


def _import_symbol(dotted_path: str) -> Any:
    module_name, _, attribute = dotted_path.rpartition(".")
    if not module_name:
        raise ImportError(f"Cannot resolve module for '{dotted_path}'")
    module = import_module(module_name)
    try:
        return getattr(module, attribute)
    except AttributeError as exc:  # pragma: no cover - defensive coding
        raise ImportError(f"Attribute '{attribute}' not found in module '{module_name}'") from exc


def _normalise_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        else:
            value = value.astimezone(UTC)
        return value.isoformat()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return [_normalise_value(item) for item in value]
    if isinstance(value, MappingABC):
        return {str(key): _normalise_value(val) for key, val in value.items()}
    return repr(value)


def _resolve_auto_audit_config(app: Flask) -> Mapping[str, Mapping[str, Any]]:
    raw = app.config.get("AUDIT_LOG_MODEL_EVENTS")
    if raw is False:  # Explicitly disabled
        return MappingProxyType({})
    if isinstance(raw, MappingABC):
        return raw or MappingProxyType({})
    if isinstance(raw, str):
        trimmed = raw.strip()
        if not trimmed:
            return _DEFAULT_AUTO_AUDIT_CONFIG
        parser = None
        try:
            parser = current_app.json  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - fallback to stdlib
            parser = None
        parsed: Any = None
        if parser is not None:
            try:
                parsed = parser.loads(trimmed)
            except Exception:
                parsed = None
        if parsed is None:
            try:
                parsed = json.loads(trimmed)
            except Exception:
                parsed = None
        if isinstance(parsed, dict):
            return parsed
        app.logger.warning("AUDIT_LOG_MODEL_EVENTS must be a JSON object; using defaults.")
    return _DEFAULT_AUTO_AUDIT_CONFIG


def _normalise_operations(raw: Any) -> frozenset[str]:
    if not raw:
        return _DEFAULT_OPERATIONS
    if isinstance(raw, str):
        candidates = {raw.strip().lower()}
    else:
        candidates = {str(item).strip().lower() for item in raw if str(item).strip()}
    selected = {item for item in candidates if item in _ALLOWED_OPERATIONS}
    return frozenset(selected or _DEFAULT_OPERATIONS)


def _build_specs(app: Flask) -> list[ModelChangeSpec]:
    config = _resolve_auto_audit_config(app)
    specs: list[ModelChangeSpec] = []
    for dotted, options in config.items():
        if not isinstance(options, MappingABC):
            app.logger.warning("Audit auto-listener entry for %s is not a mapping; skipping.", dotted)
            continue
        fields_raw = options.get("fields")
        if isinstance(fields_raw, str):
            fields = (fields_raw,)
        else:
            fields = tuple(fields_raw or ())
        if not fields:
            app.logger.warning("Audit auto-listener entry for %s has no fields; skipping.", dotted)
            continue
        try:
            model = _import_symbol(dotted)
        except ImportError as exc:
            app.logger.warning("Audit auto-listener could not import %s: %s", dotted, exc)
            continue
        entity_type = options.get("entity") or getattr(model, "__tablename__", None) or model.__name__.lower()
        identity_field = options.get("identity_field", "id")
        fallback_raw = options.get("fallback_identity", ())
        if isinstance(fallback_raw, str):
            fallback_identity = (fallback_raw,)
        else:
            fallback_identity = tuple(fallback_raw)
        operations = _normalise_operations(options.get("operations"))
        specs.append(
            ModelChangeSpec(
                model=model,
                entity_type=entity_type,
                tracked_fields=tuple(fields),
                identity_attr=identity_field,
                identity_fallbacks=fallback_identity,
                operations=operations,
            )
        )
    return specs


def _match_spec(instance: Any, specs: list[ModelChangeSpec]) -> ModelChangeSpec | None:
    for spec in specs:
        if isinstance(instance, spec.model):
            return spec
    return None


def _capture_insert(instance: Any, spec: ModelChangeSpec) -> PendingAuditChange:
    changes: dict[str, dict[str, Any]] = {}
    for field in spec.tracked_fields:
        value = _normalise_value(getattr(instance, field, None))
        changes[field] = {"old": None, "new": value}
    metadata = {"source": "orm_listener", "operation": "insert"}
    return PendingAuditChange(
        spec=spec,
        action="created",
        entity_id=spec.resolve_identity(instance),
        changes=changes,
        metadata=metadata,
        instance_ref=instance,
    )


def _capture_update(instance: Any, spec: ModelChangeSpec) -> PendingAuditChange | None:
    state = sa.inspect(instance)
    if state.transient or state.pending:
        return None
    changes: dict[str, dict[str, Any]] = {}
    for field in spec.tracked_fields:
        if field not in state.attrs:
            continue
        history = state.attrs[field].history
        if not history.has_changes():
            continue
        old_value = history.deleted[0] if history.deleted else history.unchanged[0] if history.unchanged else None
        new_value = history.added[0] if history.added else getattr(instance, field, None)
        normalised_old = _normalise_value(old_value)
        normalised_new = _normalise_value(new_value)
        if normalised_old == normalised_new:
            continue
        changes[field] = {"old": normalised_old, "new": normalised_new}
    if not changes:
        return None
    metadata = {"source": "orm_listener", "operation": "update"}
    return PendingAuditChange(
        spec=spec,
        action="updated",
        entity_id=spec.resolve_identity(instance),
        changes=changes,
        metadata=metadata,
        instance_ref=instance,
    )


def _capture_delete(instance: Any, spec: ModelChangeSpec) -> PendingAuditChange:
    changes: dict[str, dict[str, Any]] = {}
    for field in spec.tracked_fields:
        value = _normalise_value(getattr(instance, field, None))
        changes[field] = {"old": value, "new": None}
    metadata = {"source": "orm_listener", "operation": "delete"}
    return PendingAuditChange(
        spec=spec,
        action="deleted",
        entity_id=spec.resolve_identity(instance),
        changes=changes or None,
        metadata=metadata,
        instance_ref=None,
    )


def init_auto_audit(app: Flask) -> None:
    if not app.config.get("AUDIT_LOG_ENABLED", True):
        return

    storage = app.extensions.setdefault("audit_logging", {})
    if storage.get("auto_listener_registered"):
        return

    specs = _build_specs(app)
    if not specs:
        storage["auto_listener_registered"] = True
        storage["auto_listener_specs"] = []
        return

    storage["auto_listener_specs"] = specs

    def _before_flush(session, flush_context, instances):
        if not has_app_context():
            return
        if not current_app.config.get("AUDIT_LOG_ENABLED", True):
            return

        pending: list[PendingAuditChange] = session.info.setdefault(_PENDING_EVENTS_KEY, [])

        for obj in list(session.new):
            spec = _match_spec(obj, specs)
            if not spec or "insert" not in spec.operations:
                continue
            pending.append(_capture_insert(obj, spec))

        for obj in list(session.dirty):
            if obj in session.new or obj in session.deleted:
                continue
            spec = _match_spec(obj, specs)
            if not spec or "update" not in spec.operations:
                continue
            change = _capture_update(obj, spec)
            if change:
                pending.append(change)

        for obj in list(session.deleted):
            spec = _match_spec(obj, specs)
            if not spec or "delete" not in spec.operations:
                continue
            pending.append(_capture_delete(obj, spec))

    def _after_flush(session, flush_context):
        pending: list[PendingAuditChange] | None = session.info.pop(_PENDING_EVENTS_KEY, None)
        if not pending:
            return

        for event_data in pending:
            entity_id = event_data.entity_id
            if entity_id in (None, "") and event_data.instance_ref is not None:
                entity_id = event_data.spec.resolve_identity(event_data.instance_ref)
            try:
                log_change_event(
                    action=event_data.action,
                    entity_type=event_data.spec.entity_type,
                    entity_id=entity_id,
                    changes=event_data.changes,
                    metadata=event_data.metadata,
                    commit=False,
                    flush=False,
                )
            except Exception:
                session.info.setdefault(_PENDING_EVENTS_KEY, []).clear()
                raise

    def _after_commit(session):
        session.info.pop(_PENDING_EVENTS_KEY, None)

    def _after_soft_rollback(session, previous_transaction):  # pragma: no cover - defensive cleanup
        session.info.pop(_PENDING_EVENTS_KEY, None)

    event.listen(db.session, "before_flush", _before_flush)
    event.listen(db.session, "after_flush", _after_flush)
    event.listen(db.session, "after_commit", _after_commit)
    event.listen(db.session, "after_soft_rollback", _after_soft_rollback)

    storage["auto_listener_registered"] = True
