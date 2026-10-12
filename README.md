# The lab from Hands-On Linux Infrastructure

The playbooks, roles and runbooks shown in *Hands-On Linux Infrastructure* by Tom Adelstein. Every command in the book ran against these files in the author's four-computer lab. Copy them, change the addresses and names to yours, and run each playbook in check mode first.

Not here: the encrypted vault file (make your own from `host_vars/optiplex-9020/vault.example.yml`), and Garage's Helm chart (version 0.10.2, app v2.4.1, from https://git.deuxfleurs.fr/Deuxfleurs/garage.git; `k8s/garage/chart-source.sha256` holds the checksum of the copy the lab used).

## lab-ansible: the lab, in files

This repository builds and runs a four-computer Linux lab. If you have just taken the lab over, read this file, then `runbooks/restore.md` and `runbooks/alerts.md`. You should not need to call the person who built it.

## The computers

| Computer | Address | Job |
|---|---|---|
| inspiron | 192.168.12.14 (wireless 192.168.12.24) | The hardened endpoint, a Dell laptop. Carries optiplex-9020's traffic to the Internet. K3s agent. |
| optiplex-9020 | 192.168.12.15 | Git server (`/srv/git`), domain controller for `lab.internal` (Samba), the lab's clock, Prometheus and Alertmanager, Garage (the lab's object storage), and the backups of inspiron, -06 and -07. K3s agent, reserved. Stays on all night. |
| optiplex-7080 | 192.168.12.16 (wireless 192.168.12.95) | The command center: Ansible runs here, and its SSH key logs in to the others. K3s agent, reserved. Sleeps at night. |
| precision | 192.168.12.17 | The inference server: Ollama, an NVIDIA RTX 4000. K3s server. Holds optiplex-9020's backups. Reaches the Internet by Wi-Fi alone. |

The router is T-Mobile's, at 192.168.12.1, wireless only.

## Where the secrets live

Never in this repository in the clear. Each one sits in a file only its owner can read.

| Secret | Where |
|---|---|
| The SSH key that logs in to every computer | optiplex-7080, `~/.ssh/id_ed25519` |
| The Ansible Vault password | optiplex-7080, `~/.config/lab-ansible/vault-pass`, and on paper |
| The domain's Administrator password | `host_vars/optiplex-9020/vault.yml`, encrypted; open it with `ansible-vault view` |
| Each computer's restic password | on that computer, `/root/.config/restic/password`, and on paper |
| Velero's key to Garage | optiplex-7080, `~/.config/lab-velero/credentials` |
| The cluster's admin file | optiplex-7080, `~/.kube/config` |

## The playbooks

Run every playbook from this folder on optiplex-7080. `-K` asks for your sudo password.

| Playbook | What it does |
|---|---|
| `patch.yml` | Installs waiting updates |
| `harden.yml` | SSH by key from named addresses only; UFW on every computer |
| `audit.yml` | The domain controller's record of logins and password changes |
| `rotate-admin.yml` | Changes the domain's Administrator password to the one in the vault |
| `k3s.yml` | The K3s cluster: server on precision, agents on the other three |
| `backup.yml` | Nightly restic backups, each computer to a different one |
| `monitor.yml` | The node exporter everywhere; Prometheus and Alertmanager on optiplex-9020 |
| `mail-accounts.yml` | Mail, part 1: the mail server's DNS name and two staff test accounts on the domain |
| `mail.yml` | Mail, part 2: Postfix and Dovecot on precision, passwords checked against the domain |
| `mail-migrate.yml` | Mail, part 3: copies a mailbox from an old server with Dovecot's own tool and counts both sides |
| `deploy-hello.yml` | Puts the cluster's test web service in the state its file in `k8s/hello/` describes; no sudo |

`k8s/` holds what runs inside the cluster: the test web service, the storage test, Traefik's address list and Garage's settings.

## How to change the lab safely

1. Run the playbook in check mode first: `ansible-playbook patch.yml -K --check`. It changes nothing and reports what it would change.
2. Then run it on one computer: `--limit inspiron`. inspiron is the one the lab can most easily do without; optiplex-9020 goes last.
3. Before anything that touches SSH or the firewall, the roles schedule an undo command on the computer, a systemd timer that puts the old settings back after 10 minutes (harden) or 15 (k3s, backup). Prove a new login works, then stop the timer. If you lose your way in, wait: the timer brings it back.
4. Commit the change here, with the reason, and push to optiplex-9020.

## When something breaks

- An alert on Alertmanager's page: `runbooks/alerts.md`.
- Something lost: `runbooks/restore.md`. Each procedure says whether it has been drilled.
- A change that went wrong: `git revert` the commit and run the same playbook again (drilled 11 Oct 2026 with `deploy-hello.yml`).
- Write down what happened, how you fixed it and how long it took, in the commit message of the fix.
