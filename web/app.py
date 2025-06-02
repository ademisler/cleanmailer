import os
import re
import pandas as pd
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

ROOT = os.environ.get("CLEANMAILER_HOME", "/opt/cleanmailer")
INPUT_DIR = os.path.join(ROOT, "input")
LOG_DIR = os.path.join(ROOT, "logs")
RECEIVERS_PATH = os.path.join(INPUT_DIR, "Receivers.xlsx")
SENDERS_PATH = os.path.join(INPUT_DIR, "Senders.xlsx")
SEND_LOG = os.path.join(LOG_DIR, "send.log")
BOUNCE_FILE = os.path.join(ROOT, "reports", "bounced.xlsx")
REPLY_FILE = os.path.join(ROOT, "reports", "replied.xlsx")

USERNAME = "admin"
PASSWORD = "fulexo33@"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "cleanmailer-secret")


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
    bounce_count = 0
    reply_count = 0
    if os.path.exists(BOUNCE_FILE):
        bounce_count = len(pd.read_excel(BOUNCE_FILE))
    if os.path.exists(REPLY_FILE):
        reply_count = len(pd.read_excel(REPLY_FILE))
    return render_template(
        "pages/dashboard.html",
        sent_count=sent_total,
        bounce_count=bounce_count,
        reply_count=reply_count,
        line_data=per_day,
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


@app.route("/upload/<name>", methods=["POST"])
@login_required
def upload_file(name):
    uploaded = request.files.get("file")
    if not uploaded:
        flash("No file provided")
        return redirect(url_for("manage_files"))

    dest = RECEIVERS_PATH if name == "receivers" else SENDERS_PATH
    ext = os.path.splitext(uploaded.filename)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(uploaded)
        df.to_excel(dest, index=False)
    else:
        uploaded.save(dest)
    flash("File uploaded")
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
    if os.path.exists(SEND_LOG):
        with open(SEND_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()[-200:]
    else:
        lines = None
    return render_template("pages/logs.html", log_lines=lines)


if __name__ == "__main__":
    app.run(debug=True)
