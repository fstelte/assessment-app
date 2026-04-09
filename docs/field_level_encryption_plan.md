# Plan: Veldniveau-encryptie van geheimen

**Status:** Voorstel  
**Datum:** 2026-04-08  
**Auteur:** GitHub Copilot

---

## 1. Probleemstelling

Momenteel worden gevoelige gegevens onversleuteld opgeslagen in de database. Bij een database-lek (SQL-injectie, gestolen backup, ongeautoriseerde toegang) zijn deze gegevens direct leesbaar.

### Betrokken velden (hoog risico)

| Tabel | Veld | Type | Risico |
|---|---|---|---|
| `mfa_settings` | `secret` | String(64) | TOTP-secrets, volledig exploiteerbaar bij lek |
| `mfa_settings` | `backup_codes` | JSON | Eenmalige herstelcodes, plaintext in DB |

### Betrokken velden (medium risico)

| Tabel | Veld | Type | Risico |
|---|---|---|---|
| `users` | `azure_oid` | String(255) | Directe koppeling naar Entra ID identiteit |
| `users` | `aad_upn` | String(255) | E-mailadres/UPN van Azure AD gebruiker |
| `passkey_credentials` | `credential_id` | LargeBinary | Koppelbaar aan fysiek authenticatorapparaat |

---

## 2. Aanpak: Transparante SQLAlchemy `TypeDecorator`

De aanbevolen aanpak is een **herbruikbare `EncryptedType` column type** op basis van `SQLAlchemy TypeDecorator` en `cryptography.fernet.Fernet`. Dit werkt transparant: de applicatiecode hoeft niet te veranderen — encryptie/decryptie vindt automatisch plaats bij lees- en schrijfoperaties.

### Waarom Fernet?

- **Authenticated encryption** (AES-128-CBC + HMAC-SHA256): beschermt tegen manipulatie én afluisteren
- **Al beschikbaar**: `cryptography >= 46.0.6` staat al in `pyproject.toml`
- **Simpel sleutelbeheer**: één 32-byte sleutel, base64url-gecodeerd
- **Deterministisch per versleuteling**: elke encryptie produceert een unieke ciphertext (IV ingebakken)

---

## 3. Implementatieplan

### Fase 1 — Infrastructuur (geen migraties vereist)

#### 1.1 Encryptie-hulpmodule aanmaken

**Bestand:** `scaffold/core/encryption.py`

```python
from __future__ import annotations
import os
import base64
from cryptography.fernet import Fernet, MultiFernet
from sqlalchemy import String, LargeBinary, Text
from sqlalchemy.types import TypeDecorator


def _load_fernet() -> MultiFernet:
    """
    Laad één of meerdere Fernet-sleutels uit omgevingsvariabelen.
    Ondersteunt sleutelrotatie via kommagescheiden FIELD_ENCRYPTION_KEYS.
    De eerste sleutel is de actieve versleutelingssleutel.
    """
    raw = os.environ.get("FIELD_ENCRYPTION_KEYS", "")
    if not raw:
        raise RuntimeError(
            "FIELD_ENCRYPTION_KEYS is niet geconfigureerd. "
            "Genereer een sleutel met: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    keys = [Fernet(k.strip().encode()) for k in raw.split(",") if k.strip()]
    return MultiFernet(keys)


class EncryptedString(TypeDecorator):
    """Transparant versleuteld String-veld (opgeslagen als Text)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        fernet = _load_fernet()
        return fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        fernet = _load_fernet()
        return fernet.decrypt(value.encode()).decode()


class EncryptedJSON(TypeDecorator):
    """Transparant versleuteld JSON-veld (geserialiseerd als string, dan versleuteld)."""
    import json as _json
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect) -> str | None:
        import json
        if value is None:
            return None
        fernet = _load_fernet()
        serialized = json.dumps(value)
        return fernet.encrypt(serialized.encode()).decode()

    def process_result_value(self, value: str | None, dialect):
        import json
        if value is None:
            return None
        fernet = _load_fernet()
        decrypted = fernet.decrypt(value.encode()).decode()
        return json.loads(decrypted)


class EncryptedBinary(TypeDecorator):
    """Transparant versleuteld LargeBinary-veld."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: bytes | None, dialect) -> str | None:
        if value is None:
            return None
        fernet = _load_fernet()
        return fernet.encrypt(value).decode()

    def process_result_value(self, value: str | None, dialect) -> bytes | None:
        if value is None:
            return None
        fernet = _load_fernet()
        return fernet.decrypt(value.encode())
```

#### 1.2 Sleutel toevoegen aan configuratie

**Bestand:** `scaffold/config.py` — voeg toe aan de `Settings`-klasse:

```python
field_encryption_keys: str = Field(
    default="",
    description="Kommagescheiden Fernet-sleutels voor veldencryptie. Eerste = actief.",
    alias="FIELD_ENCRYPTION_KEYS",
)
```

**Bestand:** `env.production.example` — voeg toe:

```dotenv
# Veldniveau-encryptie
# Genereer een sleutel: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEYS=<genereer-en-vul-in>
```

---

### Fase 2 — Modellen aanpassen

#### 2.1 `MFASetting.secret` en `MFASetting.backup_codes`

**Bestand:** `scaffold/apps/identity/models.py`

*Voor:*
```python
secret = db.Column(db.String(64), nullable=False)
backup_codes = db.Column(db.JSON, default=list)
```

*Na:*
```python
from scaffold.core.encryption import EncryptedString, EncryptedJSON

secret = db.Column(EncryptedString, nullable=False)
backup_codes = db.Column(EncryptedJSON, default=list)
```

#### 2.2 (Optioneel, medium risico) `User.azure_oid` en `User.aad_upn`

```python
from scaffold.core.encryption import EncryptedString

azure_oid = db.Column(EncryptedString, nullable=True, index=False)
aad_upn = db.Column(EncryptedString, nullable=True, index=False)
```

> ⚠️ **Let op:** Versleutelde kolommen zijn **niet doorzoekbaar met `LIKE` of `=` queries**. Als `azure_oid`/`aad_upn` worden gebruikt als lookup-sleutel (bijv. bij SAML-login), is een **deterministische hash-index** nodig (zie Fase 4).

#### 2.3 (Optioneel, laag risico) `PasskeyCredential.credential_id`

```python
from scaffold.core.encryption import EncryptedBinary

credential_id = db.Column(EncryptedBinary, nullable=False)
```

---

### Fase 3 — Database-migraties

Na elke modelwijziging een migratie genereren en uitvoeren:

```bash
# Migratie aanmaken
poetry run flask --app scaffold:create_app db migrate -m "encrypt sensitive mfa fields"

# Reviseer de gegenereerde migratie in migrations/versions/
# Controleer op correctheid vóór uitvoering

# Toepassen
poetry run flask --app scaffold:create_app db upgrade
```

> ⚠️ **Datamigratieaandacht:** Bestaande plaintext-waarden in de database worden **niet automatisch versleuteld** door Alembic. Zie Fase 5 (datamigratiescript).

---

### Fase 4 — Zoekbare versleutelde velden (HMAC-index)

Voor velden die worden opgezocht (bijv. `azure_oid` bij authenticatie) is een **deterministisch HMAC-fingerprint** nodig als zoekindex. Fernet-encryptie is niet-deterministisch (elke run geeft andere ciphertext).

**Aanpak:** Voeg een extra `*_index` kolom toe met een HMAC-SHA256 fingerprint:

```python
import hmac, hashlib, os

def _hmac_index(value: str) -> str:
    key = os.environ["FIELD_ENCRYPTION_KEYS"].split(",")[0].strip()
    return hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()

# In User-model:
azure_oid_index = db.Column(db.String(64), nullable=True, index=True)

@staticmethod
def find_by_azure_oid(oid: str):
    return User.query.filter_by(azure_oid_index=_hmac_index(oid)).first()
```

---

### Fase 5 — Datamigratiescript

Bestaande data in de database moet worden versleuteld. Schrijf een CLI-commando (of eenmalig script):

**Bestand:** `scaffold/cli.py` — voeg toe:

```python
@app.cli.command("encrypt-existing-secrets")
def encrypt_existing_secrets():
    """Versleutel bestaande plaintext MFA-secrets en backup-codes."""
    from scaffold.apps.identity.models import MFASetting
    from scaffold.core.encryption import EncryptedString, EncryptedJSON, _load_fernet
    import json

    fernet = _load_fernet()
    count = 0

    for mfa in MFASetting.query.all():
        # Detecteer of waarde al versleuteld is (Fernet ciphertext begint met "gAAAAA")
        if mfa.secret and not mfa.secret.startswith("gAAAAA"):
            mfa.secret = fernet.encrypt(mfa.secret.encode()).decode()
        if mfa.backup_codes and isinstance(mfa.backup_codes, list):
            serialized = json.dumps(mfa.backup_codes)
            mfa.backup_codes = fernet.encrypt(serialized.encode()).decode()
        count += 1

    db.session.commit()
    click.echo(f"Versleuteld: {count} MFASetting records.")
```

Uitvoeren (éénmalig handmatig of via Docker-startup — zie Fase 5b):
```bash
poetry run flask --app scaffold:create_app encrypt-existing-secrets
```

---

### Fase 5b — Automatisch uitvoeren bij Docker-opstart

De `entrypoint.sh` voert bij elke container-start al `flask db upgrade` uit. Het migratiescript moet **direct daarna** worden aangeroepen, zodat elke deployment automatisch eventuele plaintext-records versleutelt.

Het commando is **idempotent**: records die al versleuteld zijn (ciphertext begint met `gAAAAA`) worden overgeslagen.

**Wijziging in `docker/entrypoint.sh`:**

*Voor:*
```sh
flask db upgrade

# Background cleaner: ...
start_exports_cleaner
```

*Na:*
```sh
flask db upgrade
flask encrypt-existing-secrets

# Background cleaner: ...
start_exports_cleaner
```

> ⚠️ **Vereiste:** `FIELD_ENCRYPTION_KEYS` moet aanwezig zijn in de omgevingsvariabelen vóórdat de container start. Als de variabele ontbreekt, gooit `_load_fernet()` een `RuntimeError` en stopt de container — dit is bewuste fail-fast gedrag om onversleuteld opstarten te voorkomen.

> ℹ️ **Docker Compose secrets**: Overweeg de sleutel als Docker secret te beheren in plaats van een omgevingsvariabele, zodat de waarde niet zichtbaar is in `docker inspect`:
> ```yaml
> services:
>   app:
>     secrets:
>       - field_encryption_keys
>     environment:
>       FIELD_ENCRYPTION_KEYS_FILE: /run/secrets/field_encryption_keys
> secrets:
>   field_encryption_keys:
>     file: ./secrets/field_encryption_keys.txt
> ```
> In dat geval moet `_load_fernet()` ook `FIELD_ENCRYPTION_KEYS_FILE` ondersteunen als fallback.

---

### Fase 6 — Sleutelrotatie

`MultiFernet` ondersteunt sleutelrotatie zonder downtime:

1. **Nieuwe sleutel genereren:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Beide sleutels configureren** (nieuwe sleutel eerst):
   ```dotenv
   FIELD_ENCRYPTION_KEYS=NIEUWE_SLEUTEL,OUDE_SLEUTEL
   ```
   Fernet decrypteert nu met beide sleutels, maar versleutelt met de eerste (nieuwe).

3. **Herversleutelen van bestaande data:**
   ```python
   # Voor elke rij: decrypt met oude sleutel, encrypt met nieuwe
   for mfa in MFASetting.query.all():
       plaintext = old_fernet.decrypt(mfa.secret.encode())
       mfa.secret = new_fernet.encrypt(plaintext).decode()
   db.session.commit()
   ```

4. **Oude sleutel verwijderen** uit `FIELD_ENCRYPTION_KEYS` na volledige migratie.

---

## 4. Volgorde van uitvoering

```
[ ] 1. scaffold/core/encryption.py aanmaken
[ ] 2. FIELD_ENCRYPTION_KEYS toevoegen aan config.py en env.production.example
[ ] 3. MFASetting-model aanpassen (secret, backup_codes)
[ ] 4. Alembic-migratie genereren en reviewen
[ ] 5. encrypt-existing-secrets CLI-commando toevoegen aan scaffold/cli.py
[ ] 6. docker/entrypoint.sh aanpassen: flask encrypt-existing-secrets na flask db upgrade
[ ] 7. Tests updaten / toevoegen
[ ] 8. Uitrollen naar productie:
        a. FIELD_ENCRYPTION_KEYS instellen in Docker omgevingsvariabelen / secrets
        b. Container herstarten — entrypoint voert db upgrade + encrypt automatisch uit
[ ] 9. (Optioneel) User.azure_oid / aad_upn aanpassen + HMAC-index
```

---

## 5. Teststrategie

**Bestand:** `tests/test_field_encryption.py`

```python
import pytest
from scaffold.core.encryption import EncryptedString, EncryptedJSON

def test_encrypted_string_roundtrip(app):
    with app.app_context():
        enc = EncryptedString()
        ciphertext = enc.process_bind_param("geheim", None)
        assert ciphertext != "geheim"
        assert ciphertext.startswith("gAAAAA")
        plaintext = enc.process_result_value(ciphertext, None)
        assert plaintext == "geheim"

def test_encrypted_json_roundtrip(app):
    with app.app_context():
        enc = EncryptedJSON()
        data = ["code1", "code2"]
        ciphertext = enc.process_bind_param(data, None)
        result = enc.process_result_value(ciphertext, None)
        assert result == data

def test_none_values_remain_none(app):
    with app.app_context():
        enc = EncryptedString()
        assert enc.process_bind_param(None, None) is None
        assert enc.process_result_value(None, None) is None
```

Voeg aan `conftest.py` toe:

```python
# Zorg dat FIELD_ENCRYPTION_KEYS aanwezig is in testomgeving
os.environ.setdefault(
    "FIELD_ENCRYPTION_KEYS",
    "t3xLB2zXmQvP8kRdNwJsYeHfCaGpUiOb4lV7hM1nDgA="  # testsleutel, nooit productie
)
```

---

## 6. Beveiligingsoverwegingen

| Punt | Aanbeveling |
|---|---|
| Sleutelopslag | Nooit de sleutel in de codebase committen. Gebruik Docker secrets, Vault, of omgevingsvariabelen. |
| Backup-encryptie | Databasebackups zijn waardeloos zonder de Fernet-sleutel. Sla de sleutel gescheiden van de backup op. |
| Logging | Controleer dat audit logs geen plaintext-secrets loggen. De `EncryptedType` werkt transparant, maar let op formulier-input logging. |
| Zoekbaarheid | Versleutelde kolommen zijn niet direct doorzoekbaar. Gebruik HMAC-index voor lookup-velden. |
| Key stretching | Fernet gebruikt al een ingebakken IV. De base64-sleutel moet voldoende entropie hebben (gegenereerd via `Fernet.generate_key()`). |
| Kolombreedte | Fernet-ciphertext is ~40 bytes groter dan plaintext. Pas `String(64)` aan naar `Text` of `String(200+)`. |

---

## 7. Afhankelijkheden

Geen nieuwe dependencies nodig — `cryptography` staat al in `pyproject.toml`:

```toml
cryptography = ">=46.0.6"
```

---

## 8. Beslispunten (voor bespreking)

1. **Scope high-risk only vs. all sensitive fields**: Minimaal `mfa_settings.secret` en `backup_codes` versleutelen. `azure_oid`/`aad_upn` zijn optioneel maar verhogen compliance met AVG/GDPR.
2. **Sleutelbeheer**: Docker secret vs. omgevingsvariabele vs. externe Vault (bijv. HashiCorp Vault). Voor eenvoud: omgevingsvariabele in Docker Compose secrets-sectie.
3. **Zoekstrategie voor `azure_oid`**: HMAC-index-kolom implementeren of SAML-lookup herschrijven zodat niet gezocht wordt op dit veld.
4. **Audittrail**: Willen we loggen welke records zijn herversleuteld tijdens sleutelrotatie?
