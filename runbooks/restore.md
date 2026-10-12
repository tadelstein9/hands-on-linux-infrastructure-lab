# Restore runbook

How to bring back what the lab can lose. Every procedure names the commands in the order you run them. A procedure marked **drilled** ran end to end in the lab on the date given; one marked **not drilled** follows the project's own documentation and has not run here yet. Drill it before you need it.

This file lives in Git on optiplex-9020 (`/srv/git/pipeline/lab-ansible.git`) and in the clone on optiplex-7080 (`~/lab-ansible`). optiplex-7080's nightly backup holds a third copy.

## What the lab keeps, and where

| What | Backed up by | Kept on |
|---|---|---|
| inspiron: `/etc`, `/home/tom` | restic, nightly about 02:30 | optiplex-9020, `/srv/restic/inspiron` |
| optiplex-9020: `/etc`, `/srv/git`, the domain (`/var/backups/samba`), Garage's storage | restic, nightly | precision, `/srv/restic/optiplex-9020` |
| optiplex-7080: `lab-ansible`, the Vault password file, `~/.kube`, Velero's key | restic, nightly (catches up when optiplex-7080 wakes) | optiplex-9020, `/srv/restic/optiplex-7080` |
| precision: `/etc`, the cluster's database copy and server token (`/var/backups/k3s`), the cluster's volumes | restic, nightly | optiplex-9020, `/srv/restic/precision` |
| The `lab` namespace in the cluster, its volumes included | Velero, `lab-nightly`, 04:00 UTC (11:00 p.m. Central), kept 30 days | Garage on optiplex-9020, bucket `velero` |

## The keys you need

- **Each computer's restic password.** On paper, under the computer's name. On the computer, in `/root/.config/restic/password` (root only).
- **The Ansible Vault password.** On paper. On optiplex-7080, in `~/.config/lab-ansible/vault-pass`.
- **Velero's key to Garage.** On optiplex-7080, in `~/.config/lab-velero/credentials` (tom only), and in optiplex-7080's restic backup.

restic opens a computer's backups only with that computer's password, and it refuses the owner without it. Keep the paper.

## 1. Bring back a file or a folder (restic): drilled 1 Oct 2026 on inspiron

Work on the computer that lost the file, as root.

```
sudo -i
set -a; . /etc/lab-backup/env; set +a
restic snapshots
restic ls latest /srv/git
restic restore latest --target /root/restore --include /srv/git/books
```

`restic restore` writes beside the original, under `/root/restore`, so nothing is overwritten. Compare, then copy back what you need:

```
diff -r /root/restore/srv/git/books /srv/git/books
cp -a /root/restore/srv/git/books/you-didnt-know-linux.git /srv/git/books/
rm -rf /root/restore
```

To bring back an older version, name a snapshot ID from `restic snapshots` in place of `latest`.

## 2. Bring back a program and its storage in the cluster (Velero): drilled 1 Oct 2026; run from this page alone 11 Oct 2026 (25 seconds)

Work on optiplex-7080, as tom. The drill deleted the `notes` claim and its file and brought both back in 60 seconds. On 11 Oct the handoff test ran these commands from this page and had the file readable in 25 seconds.

Velero leaves alone anything that still exists and says so as a warning ("already exists"). To restore one program, delete what is left of it first. For the notes program:

```
kubectl -n lab delete deployment notes
kubectl -n lab delete pvc notes --wait
```

Then restore. `velero backup get` lists the newest nightly backup first among the `lab-nightly-` names; use its full name, or an older one to go further back:

```
velero backup get
velero restore create --from-backup lab-nightly-<timestamp> --wait
kubectl -n lab get pods,pvc
kubectl -n lab exec deploy/notes -c shell -- cat /data/notes.txt
```

To read a restore's details or logs, run Velero inside the cluster; optiplex-7080 cannot resolve Garage's in-cluster address:

```
kubectl -n velero exec deploy/velero -c velero -- /velero restore describe <name> --details
```

## 3. Bring back the git server (optiplex-9020): restore and check drilled 1 Oct 2026, into a scratch folder; copy-back and push not drilled

The repositories are plain folders under `/srv/git`. Their backup sits on precision, in optiplex-9020's restic repository, and it is as old as the last nightly run. On optiplex-9020, as root, restore the whole folder, not only `/srv/git/books`:

```
sudo -i
set -a; . /etc/lab-backup/env; set +a
restic snapshots
restic restore latest --target /root/restore --include /srv/git
```

Check the restored copy, not the live one. Every repository should pass `git fsck`; `-c safe.directory='*'` lets root read folders the git account owns:

```
for r in $(find /root/restore/srv/git -name '*.git' -type d -prune); do git -c safe.directory='*' --git-dir="$r" fsck --no-progress >/dev/null && echo "ok $r" || echo "FAILED $r"; done
```

Copy back what you lost with `cp -a`, which keeps the git account as owner and the shared-group bit, then remove `/root/restore`.

The backup misses every push since the last nightly run. In the drill, 28 of 32 repositories matched the live copies and 4 had newer commits. Every clone on optiplex-7080 and inspiron holds its repository's full history, so finish with a push from each clone:

```
git push origin --all
```

Then check one repository from optiplex-7080:

```
git ls-remote git@192.168.12.15:/srv/git/books/you-didnt-know-linux.git HEAD
```

The drill took 23 seconds: 994.7 MiB restored in 9, every repository passed `git fsck`, and owner and permissions came back as they were.

## 4. Bring back the cluster's database (precision): not drilled

The K3s documentation: "To restore the SQLite datastore, restore the contents of `/var/lib/rancher/k3s/server/db` (and the token)." The nightly backup keeps a consistent copy of the database and the token in `/var/backups/k3s`. On precision, as root:

```
set -a; . /etc/lab-backup/env; set +a
restic restore latest --target /root/restore --include /var/backups/k3s
systemctl stop k3s
mv /var/lib/rancher/k3s/server/db /var/lib/rancher/k3s/server/db.before-restore
mkdir -p /var/lib/rancher/k3s/server/db
cp -a /root/restore/var/backups/k3s/state.db /var/lib/rancher/k3s/server/db/state.db
cp -a /root/restore/var/backups/k3s/token /var/lib/rancher/k3s/server/token
systemctl start k3s
kubectl get nodes
```

Restore the token with the database. The K3s documentation warns: "If you do not use the same token value when restoring, the snapshot will be unusable."

## 5. Bring back the domain controller (optiplex-9020): not drilled

The nightly backup keeps one tar file made by `samba-tool domain backup offline` in `/var/backups/samba`. Samba's wiki gives the restore and its conditions (checked against the page, 1 Oct 2026):

- The restored controller takes a new name; "This new DC must not have existed previously in the Samba network."
- Stop Samba on every old controller first.
- Every other computer rejoins the restored controller.

```
set -a; . /etc/lab-backup/env; set +a
restic restore latest --target /root/restore --include /var/backups/samba
samba-tool domain backup restore --backup-file=/root/restore/var/backups/samba/<the tar file> --newservername=<NEW-NAME> --targetdir=/var/lib/samba-restored
```

The wiki recommends restoring onto a temporary computer, rejoining the original controllers one at a time under their old names, then removing the temporary one with `samba-tool domain demote`. A safe first drill: "It's always safe to restore the backup-file to disk, as long as you don't actually start samba on the restored database." Plan an afternoon.

## 6. Bring back a whole computer: not drilled

1. Install Linux Mint 22.3 and give the computer its old name and address.
2. From optiplex-7080, run the roles in order: `harden.yml`, `backup.yml`, then the computer's own roles (`k3s.yml`, `monitor.yml`).
3. On the new computer, put the restic password from paper into `/root/.config/restic/password` (mode 600) before `backup.yml` runs, so the role finds the old repository instead of making a new one.
4. Restore its folders with procedure 1.

## After any restore

Write down what you lost, how you brought it back, and how long it took, in the lab's notes. Then run the next nightly backup by hand (`sudo systemctl start lab-backup`) so the restored state has a backup of its own.
