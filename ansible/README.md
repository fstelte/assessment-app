# Deployment Automation

This Ansible structure enables pipeline-driven deployments for the scaffold application. The playbooks allow switching between native (virtualenv) and Docker-based installations by setting a single variable.

## Layout

- `inventory/hosts.yml` — sample inventory.
- `group_vars/all.yml` — global defaults, including the `deployment_mode` toggle.
- `playbooks/deploy.yml` — main entry point to be used from CI/CD.
- `roles/common` — shared tasks (system packages, user setup).
- `roles/default_install` — Poetry-driven installation on the host.
- `roles/docker` — deployment using Docker Compose.

## Usage

Dry-run the deployment:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/deploy.yml --check
```

Select Docker deployment:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/deploy.yml -u deploy --extra-vars 'deployment_mode=docker'
```

Select default (system) deployment (the default value):

```bash
ansible-playbook -i inventory/hosts.yml playbooks/deploy.yml -u deploy
```

Both roles ensure migrations are executed (`flask db upgrade`) after the application is updated.
