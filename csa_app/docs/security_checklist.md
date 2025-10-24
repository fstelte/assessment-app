# Security & Compliance Checklist

- [ ] MFA verplicht voor admin-rollen; admin kan toggelen en secret delen via `admin/manage_user_mfa`.
- [ ] Registraties zijn pending totdat een admin activeert (`User.status`).
- [ ] Password policy: minimumlengte 8, gevalideerd in registratiefunctie en test `test_registration_rejects_short_password`.
- [ ] CSRF-bescherming standaard aan via `Flask-WTF`; tests zetten het uit binnen de testing-config.
- [ ] Privilege escalation tests (`test_admin_mfa_requires_admin_role`) garanderen dat alleen admins MFA-gegevens kunnen beheren.
- [ ] MFA tokens worden sanitised voordat verificatie plaatsvindt (`validate_token`).
- [ ] Control-import valideert input en logt fouten via `ImportStats.errors`.
- [ ] CI draait linting (`ruff`, `black`), security scan (`bandit`) en tests met coverage.
