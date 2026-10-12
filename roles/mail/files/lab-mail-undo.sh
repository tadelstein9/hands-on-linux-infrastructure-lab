#!/bin/sh
# Undo for the mail role: stop the mail services, close the mail ports, restore Dovecot's auth file.
systemctl stop postfix dovecot
for p in 25 587 993; do ufw delete allow from 192.168.12.0/24 to any port $p proto tcp; done
[ -f /root/before-mail/10-auth.conf ] && cp /root/before-mail/10-auth.conf /etc/dovecot/conf.d/10-auth.conf
[ -f /root/before-mail/sssd.conf ] && cp /root/before-mail/sssd.conf /etc/sssd/sssd.conf && systemctl restart sssd
