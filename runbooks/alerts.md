# Alerts runbook

What to do when an alert fires. Every alert on Alertmanager's page has an entry here: what it means, how bad it is, what to check first, and what to do. Each heading says whether the entry has been drilled. Read the alert on Alertmanager's page (from optiplex-7080, `ssh -N -L 9090:127.0.0.1:9090 -L 9093:127.0.0.1:9093 tom@192.168.12.15`, then `http://localhost:9093`), find its name below, and work down the entry.

Before you fix anything, read the logs on the computer the alert names. The alert says what happened; the logs say who and when:

```
journalctl --since "-1h" --no-pager | tail -50
grep "COMMAND=" /var/log/auth.log | tail -5
```

If a person caused it on purpose, talk to that person before you change anything.

The rules live in `roles/monitor/files/lab-rules.yml`. Change a rule there, run `ansible-playbook monitor.yml -K --limit optiplex-9020`, and change its entry here in the same commit.

## ComputerDown (critical, after 5 minutes): drilled 1 Oct 2026 on inspiron

Prometheus on optiplex-9020 has not reached a computer's node exporter for five minutes. optiplex-7080 is left out, because it sleeps at night.

1. From optiplex-7080, `ssh tom@<address>`. If the login works, the computer runs and only the exporter stopped: `systemctl status prometheus-node-exporter`, then `sudo systemctl start prometheus-node-exporter`.
2. If the login fails, check the computer itself: power, cable, screen. inspiron and optiplex-9020 sit in the rack.
3. The alert clears on the first good reading, within 30 seconds of the exporter's return.

## InternetDown (critical, after 3 minutes): not drilled

A computer cannot reach `https://deb.debian.org/`.

1. On that computer: `curl -sS -m 10 -o /dev/null https://deb.debian.org/ && echo up`.
2. If every computer reports it, the T-Mobile router or the Internet itself is down. Wait, or restart the router.
3. If only precision reports it, its Wi-Fi card lost its connection, as on 30 September at 03:22: `nmcli device status`, then `sudo nmcli con up TMOBILE-570B`. The inference server's cloud model needs this connection.
4. If only optiplex-9020 reports it, its route runs through inspiron. Check inspiron first: `sysctl -n net.ipv4.ip_forward` must read 1, and `sudo ufw status` must show the ALLOW FWD rule.

## BackupFailed (critical, after 10 minutes): happened for real 11 Oct 2026 on optiplex-7080

The last nightly backup on a computer ended in failure.

On 11 Oct 2026, optiplex-7080 resumed from suspend at 06:02:11 and its timer started the missed backup in the same second; the network card came back at 06:02:14, and at 06:02:17 SSH to optiplex-9020 failed with "No route to host". Since b840f38 each run waits up to two minutes for the repository host's SSH port. The fix: `ansible-playbook backup.yml -K --limit optiplex-7080`, which also ran the backup; the alert cleared about a minute later.

1. On that computer: `journalctl -u lab-backup -n 50 --no-pager`.
2. Check these first: the computer holding the backups (optiplex-9020, or precision for optiplex-9020) was off or unreachable; its disk is full (see DiskFilling); the restic password file is missing.
3. When the cause is fixed, run the backup by hand: `sudo systemctl start lab-backup`, then read the journal again.

## BackupLate (critical, after 30 minutes): not drilled

A computer has finished no backup in 30 hours.

1. On that computer: `systemctl list-timers lab-backup.timer --no-pager`. The timer should name a next run.
2. If the timer is missing or inactive: `sudo systemctl enable --now lab-backup.timer`.
3. A computer that was off for a day catches up when it wakes (`Persistent=true`); the alert clears after that run.

## InferenceServerDown (critical, after 5 minutes): not drilled

Ollama on precision did not answer at `http://127.0.0.1:11434/api/version`.

1. On precision: `systemctl status ollama`, then `journalctl -u ollama -n 50 --no-pager`.
2. Restart it: `sudo systemctl restart ollama`.
3. If the local model answers and the cloud model does not, see InternetDown for precision.

## ClusterNodeNotReady (critical, after 10 minutes): not drilled

Fewer than three of inspiron, optiplex-9020 and precision report Ready in the cluster. optiplex-7080 is left out, because it sleeps.

1. From optiplex-7080: `kubectl get nodes`. The one not Ready is the one to read.
2. On precision, the server: `systemctl status k3s`. On an agent: `systemctl status k3s-agent`.
3. Restart the one that stopped: `sudo systemctl restart k3s` or `sudo systemctl restart k3s-agent`.

## DiskFilling (warning, after 30 minutes): not drilled

Less than 20 percent of a computer's main disk is free.

1. On that computer: `df -h /`, then `sudo du -xh / --max-depth=2 | sort -h | tail -15`.
2. On optiplex-9020, the backups grow under `/srv/restic`. restic's nightly run already keeps only 7 daily, 4 weekly and 6 monthly snapshots; if the disk still fills, the lab has outgrown it.
3. The journal can be trimmed: `sudo journalctl --vacuum-time=4weeks`.

