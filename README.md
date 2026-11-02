# Job hunt pipeline

Daily UK dev job search: pulls from Adzuna + Reed, filters against `config.yaml`,
dedupes against a local SQLite DB, writes new matches to `digests/YYYY-MM-DD.md`.

## 1. Install dependencies

```bash
pip install requests pyyaml --break-system-packages
```

## 2. Get free API credentials

- **Adzuna**: https://developer.adzuna.com/ — sign up, create an app, you get an `app_id` and `app_key`.
- **Reed**: https://www.reed.co.uk/developers/jobseeker — sign up, you get a single API key.

You only strictly need one of the two, but both together gives better coverage.

## 3. Create your `.env` file

```bash
cat > ~/Projects/JobHunter/.env << 'EOF'
ADZUNA_APP_ID=your_id_here
ADZUNA_APP_KEY=your_key_here
REED_API_KEY=your_key_here
EOF
chmod 600 ~/Projects/JobHunter/.env
```

For a manual run (not via systemd), source it first:

```bash
set -a; source .env; set +a
python3 fetch_jobs.py
```

## 4. Edit `config.yaml`

Set your keywords, location, salary floor, and any title exclusions. Re-run any time — it's safe, already-seen jobs won't be re-added or re-listed.

## 5. Check results

```bash
cat digests/$(date +%F).md
```

## 6. Track applications

```bash
python3 track.py list                 # see everything
python3 track.py list new              # only unactioned matches
python3 track.py apply adzuna:12345    # mark applied, sets a 7-day follow-up reminder
python3 track.py apply adzuna:12345 14 # ...or a custom follow-up window
python3 track.py status adzuna:12345 interviewing "phone screen booked for Thurs"
python3 track.py followups             # anything due a nudge
```

## 7. Email the digest to your phone (optional)

The script emails the digest via Gmail whenever there are new matches (silent
on empty days, so it won't spam you). Needs a Gmail **app password**, not
your normal password:

1. Turn on 2-Step Verification on the sending Gmail account if it isn't already:
   https://myaccount.google.com/security
2. Generate an app password: https://myaccount.google.com/apppasswords
   (choose "Mail" / "Other", copy the 16-character password)
3. Add to `.env`:

```bash
GMAIL_ADDRESS=your_sending_account@gmail.com
GMAIL_APP_PASSWORD=the16charapppassword
DIGEST_TO=where_to_send_it@gmail.com
```

If `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, or `DIGEST_TO` are missing, the
script just skips emailing and prints a note — the digest file is always
written regardless.

## 8. Automate with systemd (daily 8am run)

```bash
mkdir -p ~/.config/systemd/user
cp job-hunt.service job-hunt.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now job-hunt.timer
systemctl --user list-timers  # confirm it's scheduled
```

To run it once immediately without waiting for the timer:

```bash
systemctl --user start job-hunt.service
journalctl --user -u job-hunt.service -f   # watch it run
```

## Notes

- This deliberately does **not** auto-apply to anything — it surfaces matches
  and tracks status, application and CV tailoring stay manual (or a
  claude.ai step) on purpose.
- If a source starts erroring, check `journalctl --user -u job-hunt.service`
  first — most likely an expired/rate-limited API key.
- `jobs.db` is the single source of truth for what's been seen and your
  application status. Back it up if you care about the history.
