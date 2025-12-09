"""
Reimport questions from questions.csv into database.db.

Usage:
    python tools/reimport_questions.py

It will:
1) Read questions.csv (utf-8-sig).
2) Truncate the questions table.
3) Insert all rows with options packed as JSON.

Notes:
- Keeps other tables (users, history, favorites) untouched.
- Expects CSV headers: 题号, 题干, A-E, 答案, 难度, 题型, 类别(可选)
"""

import csv
import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "questions.csv"
DB_PATH = BASE_DIR / "database.db"


def load_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def reimport():
    if not CSV_PATH.exists():
        raise SystemExit(f"CSV not found: {CSV_PATH}")
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    rows = load_rows(CSV_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")
    cur = conn.cursor()

    cur.execute("DELETE FROM questions")

    sql = """
    INSERT INTO questions (id, stem, answer, difficulty, qtype, category, options)
    VALUES (?,?,?,?,?,?,?)
    """
    count = 0
    for row in rows:
        opts = {}
        for opt in ["A", "B", "C", "D", "E"]:
            v = row.get(opt)
            if v and v.strip():
                opts[opt] = v.strip()
        cur.execute(
            sql,
            (
                row["题号"],
                row["题干"],
                row["答案"],
                row["难度"],
                row["题型"],
                row.get("类别") or "未分类",
                json.dumps(opts, ensure_ascii=False),
            ),
        )
        count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} questions from {CSV_PATH}")


if __name__ == "__main__":
    reimport()


