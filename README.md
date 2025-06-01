# Mail Automation Scripts

This repository contains small utilities for filtering email lists, checking domain validity, sending bulk emails and gathering feedback through IMAP accounts.

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Define the following environment variables before running the scripts:
   - `MAIL_OTO_HOME` (optional): root directory containing input, reports and other folders. Defaults to `/opt/mail_oto`.
   - SMTP settings (`SMTP_SENDER`, `SMTP_RECEIVER`, `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`) for `mailer.py`.
   - IMAP settings (`IMAP_HOST`, `IMAP_PORT`, `EMAIL_USER`, `EMAIL_PASS`) for `imap_dump.py`.

## Scripts

- `scripts/01_filter_existing.py` – Removes addresses already contacted and saves the remaining list to `reports/kontrol_edilmemis.xlsx`.
- `scripts/02_check_domains.py` – Verifies MX or A records for domains and splits addresses into active/inactive lists.
- `scripts/03_send_mails.py` – Sends templated emails using multiple SMTP accounts and logs the results.
- `scripts/04_check_feedback.py` – Checks sender accounts for bounces and replies.
- `scripts/05_export_clean_list.py` – Produces a final cleaned list excluding bounced addresses.
- `scripts/imap_dump.py` – Simple IMAP dump utility. Credentials must be provided via environment variables.

Most scripts rely on Excel files located in the directories under `MAIL_OTO_HOME`.
