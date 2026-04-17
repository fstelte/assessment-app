# Backup Encryption & Admin Backup/Restore UI — Implementation Plan

## Overview

Add optional Fernet encryption to the existing backup solution, and expose backup creation and restore functionality through the Flask admin interface. `cryptography` (Fernet) is already a dependency of the Flask app.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Encryption algorithm | **Fernet** (`cryptography.fernet`) | Already in Flask deps; handles IV, MAC, authenticated encryption; Python-native across all three runtimes |
| Key format | URL-safe base64, 44 chars (`Fernet.generate_key()`) | Works in env vars, easy to display/copy |
| Key storage for scheduled backups | `BACKUP_ENCRYPTION_KEY` env var **or** `$BACKUP_DIR/.encryption_key` file (shared volume) | Env var is primary; file allows runtime key updates without restarting containers |
| Admin-triggered backup execution | Python-native in Flask (SQLite: `shutil.copy2`; PostgreSQL: `subprocess pg_dump`) | Flask already has the DB URI; avoids Docker-in-Docker complexity |
| Admin-generated key propagation | Writes key to `$BACKUP_DIR/.encryption_key` (shared volume) | Scheduled backups automatically pick up the new key without restarting |
| Restore handling | Upload to Flask → decrypt in-memory → write to `RESTORE_WATCH_DIR` → existing watcher picks it up | Reuses the existing poll-based restore container unchanged |

---

## Layer 1 — Shared Encryption Utilities (Flask side)

**New file: `scaffold/apps/admin/backup_crypto.py`**

Pure Python utilities used by the Flask admin routes:

```python
from cryptography.fernet import Fernet, InvalidToken

def generate_key() -> str:
    """Generate a new Fernet key, returned as a plain string."""
    return Fernet.generate_key().decode()

def encrypt_bytes(data: bytes, key: str) -> bytes:
    """Encrypt raw bytes with the given Fernet key."""
    return Fernet(key.encode()).encrypt(data)

def decrypt_bytes(data: bytes, key: str) -> bytes:
    """Decrypt Fernet-encrypted bytes. Raises InvalidToken on failure."""
    return Fernet(key.encode()).decrypt(data)

def try_decrypt(data: bytes, keys: list) -> bytes:
    """
    Try each key in order (str or None). Returns decrypted bytes on first success.
    Raises InvalidToken if all keys fail or if data is not encrypted when a key is supplied.
    Pass None as a key to return data as-is (unencrypted fallback).
    """
    for key in keys:
        if key is None:
            return data
        try:
            return Fernet(key.encode()).decrypt(data)
        except InvalidToken:
            continue
    raise InvalidToken("No key succeeded in decrypting the backup.")
```

---

## Layer 2 — Admin Backup Utilities

**New file: `scaffold/apps/admin/backup_utils.py`**

Python backup logic called by admin routes. This avoids duplicating logic in shell scripts.

```python
import gzip, os, shutil, subprocess, tempfile
from datetime import datetime, UTC
from pathlib import Path
from .backup_crypto import encrypt_bytes, generate_key

def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

def get_backup_dir(app) -> Path:
    return Path(app.config.get("BACKUP_DIR", "/backups"))

def get_configured_key(app) -> str | None:
    """Return key from config setting, or from .encryption_key file, or None."""
    key = app.config.get("BACKUP_ENCRYPTION_KEY") or None
    if not key:
        key_file = get_backup_dir(app) / ".encryption_key"
        if key_file.exists():
            key = key_file.read_text().strip() or None
    return key

def save_encryption_key(backup_dir: Path, key: str) -> None:
    """Write key to .encryption_key file in the backup dir (shared volume)."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    key_file = backup_dir / ".encryption_key"
    key_file.write_text(key)
    key_file.chmod(0o600)

def read_backup_status(backup_dir: Path) -> dict:
    """Read backup-status.json if present."""
    status_file = backup_dir / "backup-status.json"
    if status_file.exists():
        import json
        try:
            return json.loads(status_file.read_text())
        except Exception:
            pass
    return {}

def create_sqlite_backup(db_uri: str, backup_dir: Path, encryption_key: str | None = None) -> Path:
    """
    Create a gzip-compressed SQLite backup. If encryption_key is provided,
    the .gz file is Fernet-encrypted and saved as .gz.enc.
    Returns the final backup file path.
    """
    db_path_str = db_uri.split("sqlite:///", 1)[-1] if "sqlite:///" in db_uri else db_uri.split("sqlite://", 1)[-1]
    db_path = Path(db_path_str)
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite DB not found at {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = _timestamp()
    out_gz = backup_dir / f"sqlite-{stamp}.db.gz"

    with open(db_path, "rb") as f_in, gzip.open(out_gz, "wb", compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out)

    if encryption_key:
        data = out_gz.read_bytes()
        encrypted = encrypt_bytes(data, encryption_key)
        out_enc = out_gz.with_suffix(".gz.enc")
        out_enc.write_bytes(encrypted)
        out_gz.unlink()
        return out_enc

    return out_gz

def create_postgres_backup(db_uri: str, backup_dir: Path, encryption_key: str | None = None) -> Path:
    """
    Create a gzip-compressed pg_dump backup. If encryption_key is provided,
    the .gz file is Fernet-encrypted and saved as .gz.enc.
    Returns the final backup file path.
    """
    # Normalize SQLAlchemy URI to plain postgres://
    if "+" in db_uri.split("://")[0]:
        scheme, rest = db_uri.split("://", 1)
        db_uri = "postgresql://" + rest
    elif db_uri.startswith("postgres://"):
        db_uri = "postgresql://" + db_uri[len("postgres://"):]

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = _timestamp()
    out_sql = backup_dir / f"pg_dump-{stamp}.sql"
    out_gz = out_sql.with_suffix(".sql.gz")

    result = subprocess.run(
        ["pg_dump", db_uri, "--format=plain", "--no-owner", "--no-privileges", f"--file={out_sql}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr}")

    with open(out_sql, "rb") as f_in, gzip.open(out_gz, "wb", compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out)
    out_sql.unlink()

    if encryption_key:
        data = out_gz.read_bytes()
        encrypted = encrypt_bytes(data, encryption_key)
        out_enc = out_gz.with_suffix(".gz.enc")
        out_enc.write_bytes(encrypted)
        out_gz.unlink()
        return out_enc

    return out_gz
```

---

## Layer 3 — `docker/encrypt_backup.py` (container-side script)

**New file: `docker/encrypt_backup.py`**

Called from `backup-db.sh` as `python /app/encrypt_backup.py <infile> <outfile> <key>`.

```python
#!/usr/bin/env python3
"""Encrypt a backup file using Fernet. Called from backup-db.sh."""
import sys
from cryptography.fernet import Fernet

def main():
    if len(sys.argv) != 4:
        print("Usage: encrypt_backup.py <infile> <outfile> <key>", file=sys.stderr)
        sys.exit(1)
    infile, outfile, key = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(infile, "rb") as f:
        data = f.read()
    encrypted = Fernet(key.encode()).encrypt(data)
    with open(outfile, "wb") as f:
        f.write(encrypted)

if __name__ == "__main__":
    main()
```

---

## Layer 4 — `docker/backup-db.sh` Changes

After the `.gz` file is created and `LAST_CREATED` is set, add the following block immediately before the status JSON generation section:

```sh
# --- Optional Encryption ---
# Prefer BACKUP_ENCRYPTION_KEY env var, fall back to key file on shared volume
ENC_KEY="${BACKUP_ENCRYPTION_KEY:-}"
if [ -z "$ENC_KEY" ] && [ -f "$BACKUP_DIR/.encryption_key" ]; then
  ENC_KEY=$(cat "$BACKUP_DIR/.encryption_key" | tr -d '[:space:]')
fi

if [ -n "$ENC_KEY" ] && [ -n "${LAST_CREATED:-}" ]; then
  ENCRYPTED_FILE="${LAST_CREATED}.enc"
  if python /app/encrypt_backup.py "$LAST_CREATED" "$ENCRYPTED_FILE" "$ENC_KEY"; then
    rm -f "$LAST_CREATED"
    LAST_CREATED="$ENCRYPTED_FILE"
    printf '%s - backup-db: encrypted -> %s\n' "$(timestamp)" "$ENCRYPTED_FILE"
  else
    printf '%s - backup-db: WARNING: encryption failed, keeping unencrypted file\n' "$(timestamp)" >&2
  fi
fi
```

Also copy `encrypt_backup.py` in **`docker/backup/Dockerfile`** and add `cryptography` to pip install:

```dockerfile
COPY docker/encrypt_backup.py /app/encrypt_backup.py
RUN pip install --no-cache-dir boto3 cryptography
```

---

## Layer 5 — `docker/restore/restore_db.py` Changes

1. Extend `SUPPORTED_EXTENSIONS` to include `.db.gz.enc`, `.sql.gz.enc`:
   ```python
   SUPPORTED_EXTENSIONS = {".sql", ".sql.gz", ".dump", ".dump.gz", ".db", ".db.gz", ".db.gz.enc", ".sql.gz.enc"}
   ```

2. Add a `decrypt_if_needed(path: Path) -> Path` function:
   ```python
   def decrypt_if_needed(path: Path) -> Path:
       """
       If file ends in .enc, Fernet-decrypt it (trying BACKUP_ENCRYPTION_KEY env var,
       then .encryption_key file in watch dir parent, then raise).
       Returns path to decrypted temp file (caller must delete) or original path.
       """
       if not str(path).endswith(".enc"):
           return path

       from cryptography.fernet import Fernet, InvalidToken

       data = path.read_bytes()
       keys = []
       env_key = os.getenv("BACKUP_ENCRYPTION_KEY", "").strip()
       if env_key:
           keys.append(env_key)
       key_file = Path(os.getenv("RESTORE_WATCH_DIR", "/restore/incoming")).parent / ".encryption_key"
       if key_file.exists():
           file_key = key_file.read_text().strip()
           if file_key and file_key not in keys:
               keys.append(file_key)

       for key in keys:
           try:
               decrypted = Fernet(key.encode()).decrypt(data)
               # Write to temp file with the .enc extension stripped
               suffix = path.name[:-4]  # strip .enc
               tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
               tmp.write(decrypted)
               tmp.close()
               log(f"decrypted {path.name} -> {tmp.name}")
               return Path(tmp.name)
           except InvalidToken:
               continue

       raise RuntimeError(f"Could not decrypt {path}: no valid key found")
   ```

3. In `main()`, before calling `restore_sqlite()` or `restore_postgres()`, add:
   ```python
   work_path = decrypt_if_needed(backup_path)
   try:
       # pass work_path instead of backup_path to restore functions
   finally:
       if work_path != backup_path:
           work_path.unlink(missing_ok=True)
   ```

4. Add `cryptography` to **`docker/restore/Dockerfile`** pip install.

---

## Layer 6 — Flask Admin Forms

**In `scaffold/apps/admin/forms.py`**, add:

```python
from wtforms import PasswordField
from wtforms.validators import Optional, Length
from flask_wtf.file import FileAllowed, FileField, FileRequired

class BackupCreateForm(FlaskForm):
    """Trigger an admin-initiated encrypted backup."""
    submit = SubmitField(_label("admin.backup.create.submit"))

class BackupRestoreForm(FlaskForm):
    """Upload a backup file for restore, with optional encryption key."""
    backup_file = FileField(
        _label("admin.backup.restore.file_label"),
        validators=[
            FileRequired(message=_message("admin.backup.restore.file_required")),
            FileAllowed(
                ["gz", "enc", "db", "sql", "dump"],
                message=_message("admin.backup.restore.file_type"),
            ),
        ],
    )
    encryption_key = PasswordField(
        _label("admin.backup.restore.key_label"),
        validators=[Optional(), Length(max=128)],
        description=_l("admin.backup.restore.key_help"),
    )
    submit = SubmitField(_label("admin.backup.restore.submit"))
```

---

## Layer 7 — Flask Admin Routes

**In `scaffold/apps/admin/routes.py`**, add the following imports and three new routes.

### New imports
```python
from .backup_crypto import generate_key
from .backup_utils import (
    create_sqlite_backup,
    create_postgres_backup,
    get_backup_dir,
    get_configured_key,
    read_backup_status,
    save_encryption_key,
)
from .forms import BackupCreateForm, BackupRestoreForm
from .backup_crypto import try_decrypt
```

### Route 1 — Backup Dashboard
```python
@admin_bp.route("/backup")
@require_fresh_login()
@login_required
def backup_dashboard():
    _require_admin()
    backup_dir = get_backup_dir(current_app)
    status = read_backup_status(backup_dir)
    has_key = bool(get_configured_key(current_app))
    create_form = BackupCreateForm()
    return render_template(
        "admin/backup.html",
        status=status,
        has_key=has_key,
        create_form=create_form,
    )
```

### Route 2 — Create Encrypted Backup
```python
@admin_bp.route("/backup/create", methods=["POST"])
@require_fresh_login()
@login_required
def create_backup():
    _require_admin()
    form = BackupCreateForm()
    if not form.validate_on_submit():
        abort(400)

    # Generate a new key and persist it to the shared volume
    new_key = generate_key()
    backup_dir = get_backup_dir(current_app)
    save_encryption_key(backup_dir, new_key)

    # Determine DB type and run backup
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    try:
        if "sqlite" in db_uri:
            backup_path = create_sqlite_backup(db_uri, backup_dir, encryption_key=new_key)
        else:
            backup_path = create_postgres_backup(db_uri, backup_dir, encryption_key=new_key)
    except Exception as exc:
        flash(_("admin.backup.create.error", error=str(exc)), "error")
        return redirect(url_for("admin.backup_dashboard"))

    # Render page with one-time key display (do NOT redirect — key must show once)
    backup_dir_check = get_backup_dir(current_app)
    status = read_backup_status(backup_dir_check)
    create_form = BackupCreateForm()
    return render_template(
        "admin/backup.html",
        status=status,
        has_key=True,
        create_form=create_form,
        new_key=new_key,          # shown once, not stored in session
        new_backup_file=backup_path.name,
    )
```

### Route 3 — Restore a Backup
```python
@admin_bp.route("/backup/restore", methods=["GET", "POST"])
@require_fresh_login()
@login_required
def restore_backup():
    _require_admin()
    form = BackupRestoreForm()
    if form.validate_on_submit():
        uploaded = form.backup_file.data
        provided_key = form.encryption_key.data.strip() if form.encryption_key.data else None
        configured_key = get_configured_key(current_app)

        file_bytes = uploaded.read()
        filename = uploaded.filename

        # Decrypt if needed: try provided key first, then configured key, then raw
        if filename.endswith(".enc"):
            from cryptography.fernet import InvalidToken
            keys_to_try = [k for k in [provided_key, configured_key] if k]
            if not keys_to_try:
                # Try without decryption as last resort (will likely fail at restore)
                keys_to_try = [None]
            try:
                from .backup_crypto import try_decrypt
                file_bytes = try_decrypt(file_bytes, keys_to_try + [None])
                filename = filename[:-4]  # strip .enc
            except InvalidToken:
                flash(_("admin.backup.restore.decrypt_failed"), "error")
                return render_template("admin/backup_restore.html", form=form)

        # Write decrypted/plain file to RESTORE_WATCH_DIR for the restore container
        restore_dir = current_app.config.get("RESTORE_WATCH_DIR", "/restore/incoming")
        dest = Path(restore_dir) / filename
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(file_bytes)
        except Exception as exc:
            flash(_("admin.backup.restore.write_error", error=str(exc)), "error")
            return render_template("admin/backup_restore.html", form=form)

        flash(_("admin.backup.restore.queued", filename=filename), "success")
        return redirect(url_for("admin.backup_dashboard"))

    return render_template("admin/backup_restore.html", form=form)
```

---

## Layer 8 — Templates

### `scaffold/apps/admin/templates/admin/backup.html`

Use Tailwind CSS throughout, matching the existing admin style (see `users.html` for reference).

Key sections:
1. **Page header** with nav links (same pattern as `users.html` header)
2. **Backup status card** — shows `status.last_backup`, `status.last_file`, lists `status.backups[]`; indicates encryption status per file (.enc extension)
3. **Create Encrypted Backup card** — POST form with CSRF (`create_form.hidden_tag()`), single submit button
4. **One-time key display** (shown only when `new_key` is in context):
   - Amber/yellow alert box
   - Warning: "This key is shown **once**. Save it securely before leaving this page."
   - Monospace `<code>` block containing `{{ new_key }}`
   - "Copy to clipboard" button using `navigator.clipboard.writeText('{{ new_key }}')`
   - Shows which backup file was created: `{{ new_backup_file }}`
5. **"Restore a Backup" link** → `url_for('admin.restore_backup')`

### `scaffold/apps/admin/templates/admin/backup_restore.html`

Key sections:
1. **Page header** — back link to `url_for('admin.backup_dashboard')`
2. **Upload form** with:
   - File input for the backup file (`.gz`, `.gz.enc`, `.db`, `.sql`, `.dump`)
   - Optional password field for encryption key, with help text:
     *"If the backup is encrypted, enter the key used when it was created. If left empty, the configured encryption key will be tried automatically."*
   - Submit button

---

## Layer 9 — Config & Environment

### `scaffold/config.py`

Add to the `Settings` dataclass:

```python
backup_dir: str = field(default_factory=lambda: os.getenv("BACKUP_DIR", "/backups"))
backup_encryption_key: str | None = field(default_factory=lambda: os.getenv("BACKUP_ENCRYPTION_KEY") or None)
restore_watch_dir: str = field(default_factory=lambda: os.getenv("RESTORE_WATCH_DIR", "/restore/incoming"))
```

Add to `flask_config()` return dict:

```python
"BACKUP_DIR": self.backup_dir,
"BACKUP_ENCRYPTION_KEY": self.backup_encryption_key,
"RESTORE_WATCH_DIR": self.restore_watch_dir,
```

### `env.production.example`

Add in the backup section:

```bash
# Backup encryption (optional — leave empty for unencrypted backups)
BACKUP_ENCRYPTION_KEY=
```

### `example.compose.backup.yml`

Add to `db-backup` service environment:

```yaml
- BACKUP_ENCRYPTION_KEY=${BACKUP_ENCRYPTION_KEY:-}
```

Add `encrypt_backup.py` copy to the backup `Dockerfile`:

```dockerfile
COPY docker/encrypt_backup.py /app/encrypt_backup.py
RUN pip install --no-cache-dir boto3 cryptography
```

---

## Layer 10 — Admin Navigation

In `scaffold/apps/admin/templates/admin/users.html` (and any admin nav/sidebar), add a "Backup & Restore" link:

```html
<a class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-[var(--color-border)] text-[var(--color-text)] hover:bg-white/5"
   href="{{ url_for('admin.backup_dashboard') }}">
  {{ _('admin.backup.nav_link') }}
</a>
```

---

## Translation Keys Required

Add to the relevant `.po`/`.pot` translation files:

```
admin.backup.nav_link
admin.backup.create.submit
admin.backup.create.error
admin.backup.restore.file_label
admin.backup.restore.file_required
admin.backup.restore.file_type
admin.backup.restore.key_label
admin.backup.restore.key_help
admin.backup.restore.submit
admin.backup.restore.decrypt_failed
admin.backup.restore.write_error
admin.backup.restore.queued
```

---

## Implementation Order

1. `scaffold/apps/admin/backup_crypto.py`
2. `docker/encrypt_backup.py`
3. `docker/backup-db.sh` — add encryption block
4. `docker/backup/Dockerfile` — add `cryptography`, copy `encrypt_backup.py`
5. `docker/restore/restore_db.py` — extend extensions + add `decrypt_if_needed`
6. `docker/restore/Dockerfile` — add `cryptography`
7. `scaffold/apps/admin/backup_utils.py`
8. `scaffold/config.py` — add three settings
9. `env.production.example` — add `BACKUP_ENCRYPTION_KEY`
10. `example.compose.backup.yml` — passthrough env var
11. `scaffold/apps/admin/forms.py` — add `BackupCreateForm`, `BackupRestoreForm`
12. `scaffold/apps/admin/routes.py` — add three routes + imports
13. `scaffold/apps/admin/templates/admin/backup.html`
14. `scaffold/apps/admin/templates/admin/backup_restore.html`
15. `scaffold/apps/admin/templates/admin/users.html` — add nav link
16. Translation files — add required keys

## What Is NOT Changed

- Existing backup schedule and polling/interval logic
- Existing restore watcher mechanism (only extended, not replaced)
- Existing admin routes (only new routes added)
- Database schema (no new models — key stored in file, not DB)
- Any other Flask blueprints or modules
