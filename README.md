# CleanMailer

This repository contains small utilities for filtering email lists, checking domain validity, sending bulk emails and gathering feedback through IMAP accounts.

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and adjust values as needed. Important keys:
   - `CLEANMAILER_HOME` (optional): root directory containing input, reports and other folders. Defaults to `/opt/clean_mailer`.
   - SMTP settings (`SMTP_SENDER`, `SMTP_RECEIVER`, `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`) for `mailer.py`.
   - IMAP settings (`IMAP_HOST`, `IMAP_PORT`, `EMAIL_USER`, `EMAIL_PASS`) for `imap_dump.py`.
   - `ADMIN_USER`, `ADMIN_PASS` and `FLASK_SECRET` for the web panel.
3. Ensure a `logs/` directory exists under `CLEANMAILER_HOME`. Most scripts will create it automatically if missing.

## Scripts

- `scripts/01_filter_existing.py` – Removes addresses already contacted and saves the remaining list to `reports/kontrol_edilmemis.xlsx`.
- `scripts/02_check_domains.py` – Verifies MX or A records for domains and splits addresses into active/inactive lists.
- `scripts/03_send_mails.py` – Sends templated emails using multiple SMTP accounts and logs the results.
- `scripts/04_check_feedback.py` – Checks sender accounts for bounces and replies.
- `scripts/05_export_clean_list.py` – Produces a final cleaned list excluding bounced addresses.
- `scripts/imap_dump.py` – Simple IMAP dump utility. Credentials must be provided via environment variables.

Most scripts rely on Excel files located in the directories under `CLEANMAILER_HOME`.

## Web Panel

The Flask based panel allows uploading mailing lists, monitoring logs and launching
scripts directly from the browser. Cron jobs can also be managed through the UI.

### Running

```bash
export FLASK_APP=web.app
flask run
```

### Running tests

```bash
pytest
```
