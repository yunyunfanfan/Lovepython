import csv
from pathlib import Path

# Target CSV
FILE_PATH = Path(__file__).resolve().parent.parent / "questions.csv"

# Keyword-based categories
KEYWORDS = [
    ("字符串", "字符串"),
    ("string", "字符串"),
    ("列表", "列表"),
    ("list", "列表"),
    ("字典", "字典"),
    ("dict", "字典"),
    ("集合", "集合"),
    ("set", "集合"),
    ("函数", "函数"),
    ("参数", "函数"),
    ("lambda", "函数"),
    ("闭包", "函数"),
    ("类", "面向对象"),
    ("对象", "面向对象"),
    ("继承", "面向对象"),
    ("多态", "面向对象"),
    ("异常", "异常处理"),
    ("try", "异常处理"),
    ("except", "异常处理"),
    ("文件", "文件IO"),
    ("open", "文件IO"),
    ("模块", "模块与包"),
    ("import", "模块与包"),
    ("包", "模块与包"),
    ("循环", "控制流"),
    ("for", "控制流"),
    ("while", "控制流"),
    ("条件", "控制流"),
    ("if", "控制流"),
    ("推导式", "推导式"),
    ("生成器", "迭代与生成器"),
    ("迭代", "迭代与生成器"),
    ("切片", "序列操作"),
    ("range", "序列操作"),
    ("运算符", "语法基础"),
    ("关键字", "语法基础"),
    ("装饰器", "装饰器"),
    ("上下文", "上下文管理"),
    ("线程", "并发"),
    ("进程", "并发"),
    ("异步", "并发"),
]


def infer_category(stem: str) -> str:
    text = (stem or "").lower()
    for kw, cat in KEYWORDS:
        if kw.lower() in text:
            return cat
    return "Python基础"


def main() -> None:
    if not FILE_PATH.exists():
        raise SystemExit(f"questions.csv not found at {FILE_PATH}")

    with FILE_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "类别" not in fieldnames:
        fieldnames.append("类别")

    for row in rows:
        if not row.get("类别"):
            row["类别"] = infer_category(row.get("题干", ""))

    with FILE_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {len(rows)} rows with categories. Fields: {fieldnames}")


if __name__ == "__main__":
    main()


