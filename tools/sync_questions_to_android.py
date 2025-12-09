"""
Sync updated questions.csv into the Android app assets.

Usage:
    python tools/sync_questions_to_android.py

It copies:
    questions.csv  -> ExamMasterAndroid/app/src/main/assets/questions.csv
"""

from pathlib import Path
import shutil


BASE_DIR = Path(__file__).resolve().parent.parent
SRC = BASE_DIR / "questions.csv"
DST = BASE_DIR / "ExamMasterAndroid" / "app" / "src" / "main" / "assets" / "questions.csv"


def main():
    if not SRC.exists():
        raise SystemExit(f"Source not found: {SRC}")
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, DST)
    print(f"Copied {SRC} -> {DST}")


if __name__ == "__main__":
    main()


