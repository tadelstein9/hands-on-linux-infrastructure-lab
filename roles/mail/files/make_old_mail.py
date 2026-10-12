#!/usr/bin/env python3
"""make_old_mail.py MAILDIR: write a SYNTHETIC mailbox, the stand-in for one staff member's
mail on the district's old Exchange server. Invented senders and messages; seeded, so every
run writes the same 100 messages: 60 in INBOX, 25 in Sent, 15 in "Field Trips"."""
import os, random, sys, time, email.utils
root = sys.argv[1]; rng = random.Random(7)
people = ["Linda Ragsdale", "Paul Tatum", "Ruth Womack", "Carl Bivens", "Ann Crowder", "Joe Easley"]
topics = ["Lab schedule", "Chromebook cart", "Grades due Friday", "Parent night", "Printer in room 12", "Substitute plans"]
def box(name):
    d = root if name == "INBOX" else os.path.join(root, "." + name)
    for sub in ("cur", "new", "tmp"): os.makedirs(os.path.join(d, sub), exist_ok=True)
    return d
def write(name, n, sent):
    d = box(name)
    for i in range(n):
        who = rng.choice(people); t = 1788000000 + i * 3600 * 7
        frm, to = ("Ruth Quarles <rquarles@lab.internal>", f"{who} <{who.split()[1].lower()}@renfro.example>") if sent else (f"{who} <{who.split()[1].lower()}@renfro.example>", "Ruth Quarles <rquarles@lab.internal>")
        subj = f"{rng.choice(topics)} ({name} {i + 1})" if name != "Field Trips" else f"Field trip {i + 1}: permission slips"
        msg = (f"From: {frm}\nTo: {to}\nSubject: {subj}\nDate: {email.utils.formatdate(t)}\n"
               f"Message-ID: <{name.replace(' ', '')}.{i}@old.renfro.example>\n\nSynthetic message for the Chapter 7 migration test.\n")
        with open(os.path.join(d, "cur", f"{t}.{name.replace(' ', '')}{i}.old:2,S"), "w") as f: f.write(msg)
write("INBOX", 60, False); write("Sent", 25, True); write("Field Trips", 15, False)
print("wrote 100 messages to", root)
