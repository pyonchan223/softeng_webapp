"""今日のサボり言い訳ジェネレーター - Flask アプリ本体。"""

import os
import sqlite3
from datetime import datetime, timezone, timedelta

from flask import Flask, g, redirect, render_template, request, url_for

import excuses

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "excuses.db"))
JST = timezone(timedelta(hours=9))

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute(
            """CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                situation TEXT NOT NULL,
                seriousness INTEGER NOT NULL,
                text TEXT NOT NULL,
                risk INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM history ORDER BY id DESC LIMIT 10"
    ).fetchall()
    result = None
    result_id = request.args.get("r")
    if result_id and result_id.isdigit():
        result = db.execute(
            "SELECT * FROM history WHERE id = ?", (int(result_id),)
        ).fetchone()
    return render_template(
        "index.html",
        situations=excuses.SITUATIONS,
        result=result,
        risk_comment=excuses.risk_comment,
        situation_labels=excuses.SITUATIONS,
        history=rows,
    )


@app.route("/generate", methods=["POST"])
def generate():
    situation = request.form.get("situation", "class")
    try:
        seriousness = int(request.form.get("seriousness", 3))
    except ValueError:
        seriousness = 3
    if situation not in excuses.SITUATIONS:
        situation = "class"

    ex = excuses.generate(situation, seriousness)

    db = get_db()
    cur = db.execute(
        "INSERT INTO history (situation, seriousness, text, risk, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            ex["situation"],
            ex["seriousness"],
            ex["text"],
            ex["risk"],
            datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        ),
    )
    db.commit()
    return redirect(url_for("index", r=cur.lastrowid))


@app.route("/clear", methods=["POST"])
def clear():
    db = get_db()
    db.execute("DELETE FROM history")
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
