import os
import pandas as pd
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

ROOT = os.environ.get("CLEANMAILER_HOME", "/opt/cleanmailer")
INPUT_DIR = os.path.join(ROOT, "input")
RECEIVERS_PATH = os.path.join(INPUT_DIR, "Receivers.xlsx")
SENDERS_PATH = os.path.join(INPUT_DIR, "Senders.xlsx")

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


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form.get("username") == USERNAME
            and request.form.get("password") == PASSWORD
        ):
            session["logged_in"] = True
            return redirect(url_for("index"))
        flash("Invalid credentials")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    files = {
        "receivers": RECEIVERS_PATH,
        "senders": SENDERS_PATH,
    }
    path_exists = {key: os.path.exists(path) for key, path in files.items()}
    return render_template("index.html", files=files, path_exists=path_exists)


@app.route("/upload/<name>", methods=["POST"])
@login_required
def upload_file(name):
    uploaded = request.files.get("file")
    if not uploaded:
        flash("No file provided")
        return redirect(url_for("index"))

    dest = RECEIVERS_PATH if name == "receivers" else SENDERS_PATH
    ext = os.path.splitext(uploaded.filename)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(uploaded)
        df.to_excel(dest, index=False)
    else:
        uploaded.save(dest)
    flash("File uploaded")
    return redirect(url_for("index"))


@app.route("/delete/<name>", methods=["POST"])
@login_required
def delete_file(name):
    dest = RECEIVERS_PATH if name == "receivers" else SENDERS_PATH
    if os.path.exists(dest):
        os.remove(dest)
        flash("File deleted")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)

