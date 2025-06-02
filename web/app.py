import os
import re
import shutil
from datetime import datetime, timedelta
import pandas as pd
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file,
)

ROOT = os.environ.get("CLEANMAILER_HOME", "/opt/cleanmailer")
INPUT_DIR = os.path.join(ROOT, "input")
LOG_DIR = os.path.join(ROOT, "logs")
RECEIVERS_PATH = os.path.join(INPUT_DIR, "Receivers.xlsx")
SENDERS_PATH = os.path.join(INPUT_DIR, "Senders.xlsx")
BACKUP_DIR = os.path.join(ROOT, "backups")
SEND_LOG = os.path.join(LOG_DIR, "send.log")
BOUNCE_FILE = os.path.join(ROOT, "reports", "bounced.xlsx")
REPLY_FILE = os.path.join(ROOT, "reports", "replied.xlsx")

USERNAME = "admin"
PASSWORD = "fulexo33@"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "cleanmailer-secret")

os.makedirs(BACKUP_DIR, exist_ok=True)


@app.template_filter("basename")
def basename_filter(value):
    return os.path.basename(value)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


def parse_send_log():
    total = 0
    per_day = {}
    if not os.path.exists(SEND_LOG):
        return total, per_day
    date = None
    date_re = re.compile(r"(\d{4}-\d{2}-\d{2})")
    with open(SEND_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            m = date_re.search(line)
            if "Gönderim Başladı" in line and m:
                date = m.group(1)
                per_day.setdefault(date, 0)
            elif line.startswith("[OK]"):
                total += 1
                if date:
                    per_day[date] = per_day.get(date, 0) + 1
    return total, per_day


def backup_file(path: str):
    """Copy existing file to backup directory with timestamp."""
    if os.path.exists(path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(path, os.path.join(BACKUP_DIR, f"{ts}_{os.path.basename(path)}"))


def load_dataframe(path: str) -> pd.DataFrame:
    """Load Excel file if it exists otherwise return empty DataFrame."""
    if os.path.exists(path):
        return pd.read_excel(path)
    return pd.DataFrame()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == USERNAME and request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            flash("Logged in successfully.")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "error")
    return render_template("pages/login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def root():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    sent_total, per_day = parse_send_log()

    range_opt = request.args.get("range", "all")
    if range_opt == "7":
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        per_day = {d: c for d, c in per_day.items() if d >= start}
    elif range_opt == "30":
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        per_day = {d: c for d, c in per_day.items() if d >= start}
    elif range_opt == "today":
        today = datetime.now().strftime("%Y-%m-%d")
        per_day = {d: c for d, c in per_day.items() if d == today}

    bounce_count = 0
    reply_count = 0
    if os.path.exists(BOUNCE_FILE):
        bounce_count = len(pd.read_excel(BOUNCE_FILE))
    if os.path.exists(REPLY_FILE):
        reply_count = len(pd.read_excel(REPLY_FILE))

    campaign_stats = {}
    if os.path.exists(RECEIVERS_PATH):
        df_recv = pd.read_excel(RECEIVERS_PATH)
        if "campaign_id" in df_recv.columns:
            campaign_stats = df_recv["campaign_id"].value_counts().to_dict()

    return render_template(
        "pages/dashboard.html",
        sent_count=sent_total,
        bounce_count=bounce_count,
        reply_count=reply_count,
        line_data=per_day,
        range_opt=range_opt,
        campaign_stats=campaign_stats,
    )


@app.route("/files")
@login_required
def manage_files():
    files = {
        "receivers": RECEIVERS_PATH,
        "senders": SENDERS_PATH,
    }
    path_exists = {key: os.path.exists(path) for key, path in files.items()}
    return render_template("pages/manage_files.html", files=files, path_exists=path_exists)


@app.route("/download/<name>")
@login_required
def download_file(name):
    path = RECEIVERS_PATH if name == "receivers" else SENDERS_PATH
    return send_file(path, as_attachment=True)


@app.route("/example/receivers")
@login_required
def download_receivers_example():
    return send_file("static/examples/receivers_example.csv", as_attachment=True)


@app.route("/example/senders")
@login_required
def download_senders_example():
    return send_file("static/examples/senders_example.csv", as_attachment=True)


@app.route("/upload/<name>", methods=["POST"])
@login_required
def upload_file(name):
    uploaded = request.files.get("file")
    if not uploaded:
        flash("No file provided")
        return redirect(url_for("manage_files"))

    ext = os.path.splitext(uploaded.filename)[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        flash("Unsupported file type")
        return redirect(url_for("manage_files"))

    if ext == ".csv":
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)

    required_columns = {"email"} if name == "receivers" else {
        "Mail",
        "Mdp",
        "IMAP Host",
        "IMAP Port",
        "SMTP Host",
        "SMTP Port",
        "Nom",
        "Günlük Limit",
    }
    if not required_columns.issubset(df.columns):
        flash("Invalid file headers", "error")
        return redirect(url_for("manage_files"))

    session[f"pending_{name}"] = df.to_json(orient="split")
    return render_template(
        "pages/preview_upload.html",
        name=name,
        table=df.head(10).to_html(classes="table table-sm table-bordered", index=False),
    )


@app.route("/confirm_upload/<name>", methods=["POST"])
@login_required
def confirm_upload(name):
    data = session.pop(f"pending_{name}", None)
    if not data:
        flash("No pending upload")
        return redirect(url_for("manage_files"))
    df = pd.read_json(data, orient="split")
    dest = RECEIVERS_PATH if name == "receivers" else SENDERS_PATH
    if name == "receivers":
        existing = load_dataframe(dest)
        combined = pd.concat([existing, df], ignore_index=True)
        dup_count = combined.duplicated(subset=["email"]).sum()
        combined = combined.drop_duplicates(subset=["email"], keep="first")
        df = combined
        if dup_count:
            flash(f"Skipped {dup_count} duplicate emails.")
    backup_file(dest)
    df.to_excel(dest, index=False)
    flash("File uploaded")
    return redirect(url_for("manage_files"))


@app.route("/add_receiver", methods=["POST"])
@login_required
def add_receiver():
    email = request.form.get("email")
    campaign = request.form.get("campaign_id")
    if not email:
        flash("Email required")
        return redirect(url_for("manage_files"))
    df = load_dataframe(RECEIVERS_PATH)
    if "email" in df.columns and email in df["email"].values:
        flash("This email already exists in the list.")
        return redirect(url_for("manage_files"))
    new = {"email": email}
    if campaign:
        new["campaign_id"] = campaign
        if "campaign_id" not in df.columns:
            df["campaign_id"] = df.get("campaign_id")  # ensure column exists
    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
    backup_file(RECEIVERS_PATH)
    df.to_excel(RECEIVERS_PATH, index=False)
    flash("Receiver added")
    return redirect(url_for("manage_files"))


@app.route("/add_sender", methods=["POST"])
@login_required
def add_sender():
    cols = ["Mail", "Mdp", "IMAP Host", "IMAP Port", "SMTP Host", "SMTP Port", "Nom", "Günlük Limit"]
    data = {c: request.form.get(c) for c in cols}
    if not all(data.values()):
        flash("All sender fields required")
        return redirect(url_for("manage_files"))
    df = load_dataframe(SENDERS_PATH)
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    backup_file(SENDERS_PATH)
    df.to_excel(SENDERS_PATH, index=False)
    flash("Sender added")
    return redirect(url_for("manage_files"))


@app.route("/delete/<name>", methods=["POST"])
@login_required
def delete_file(name):
    dest = RECEIVERS_PATH if name == "receivers" else SENDERS_PATH
    if os.path.exists(dest):
        os.remove(dest)
        flash("File deleted")
    return redirect(url_for("manage_files"))


@app.route("/logs")
@login_required
def view_logs():
    logs = {}
    if os.path.exists(SEND_LOG):
        date_re = re.compile(r"(\d{4}-\d{2}-\d{2})")
        with open(SEND_LOG, "r", encoding="utf-8") as f:
            for line in f.readlines()[-500:]:
                line = line.strip()
                m = date_re.search(line)
                date = m.group(1) if m else "Unknown"
                logs.setdefault(date, []).append(line)
    else:
        logs = None
    return render_template("pages/logs.html", logs=logs)


if __name__ == "__main__":
    app.run(debug=True)
