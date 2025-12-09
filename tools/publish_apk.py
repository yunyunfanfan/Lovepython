"""
Publish the latest built APK to Flask static/apk for download.

Usage:
    python tools/publish_apk.py

What it does:
1) Finds the newest *.apk under ExamMasterAndroid/app/build/outputs/apk
   (if不存在则回退为整个 ExamMasterAndroid 目录递归搜索)
2) Copies it to static/apk/ with its original filename
3) Also writes/updates static/apk/latest.apk pointing to the same file (hard copy)
"""

import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
APK_ROOT = BASE / "ExamMasterAndroid" / "app" / "build" / "outputs" / "apk"
APK_FALLBACK_ROOT = BASE / "ExamMasterAndroid"
STATIC_APK_DIR = BASE / "static" / "apk"


def find_latest_apk():
    # 优先使用标准输出目录的 APK
    primary_apks = []
    if APK_ROOT.exists():
        primary_apks = sorted(APK_ROOT.rglob("*.apk"), key=lambda p: p.stat().st_mtime, reverse=True)
    if primary_apks:
        return primary_apks[0]

    # 若主目录没有，再回退整个工程目录查找
    fallback_apks = []
    if APK_FALLBACK_ROOT.exists():
        fallback_apks = sorted(APK_FALLBACK_ROOT.rglob("*.apk"), key=lambda p: p.stat().st_mtime, reverse=True)
    if fallback_apks:
        return fallback_apks[0]

    raise FileNotFoundError(
        f"No APK found under {APK_ROOT} or {APK_FALLBACK_ROOT}. "
        "Please run a build first (e.g., ./gradlew assembleDebug)."
    )


def publish():
    latest = find_latest_apk()
    STATIC_APK_DIR.mkdir(parents=True, exist_ok=True)

    dest = STATIC_APK_DIR / latest.name
    shutil.copy2(latest, dest)

    # Also provide a stable name for template linking
    stable = STATIC_APK_DIR / "latest.apk"
    shutil.copy2(dest, stable)

    print(f"Published APK:\n  source: {latest}\n  saved:  {dest}\n  stable: {stable}")


if __name__ == "__main__":
    publish()


