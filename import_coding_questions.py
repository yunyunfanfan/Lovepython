#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导入编程题到数据库
运行此脚本可以将 questions.csv 中的编程题导入到数据库
"""
import sqlite3
import csv
import json
import os

def import_coding_questions():
    """导入编程题到数据库"""
    # 连接数据库
    db_path = 'database.db'
    if not os.path.exists(db_path):
        print(f"错误：数据库文件 {db_path} 不存在！")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 检查CSV文件
    csv_path = 'questions.csv'
    if not os.path.exists(csv_path):
        print(f"错误：CSV文件 {csv_path} 不存在！")
        conn.close()
        return
    
    # 读取CSV文件
    imported_count = 0
    updated_count = 0
    error_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 只处理编程题
                qtype = row.get('题型', '').strip()
                if qtype != '编程题':
                    continue
                
                try:
                    # 构建选项字典
                    options = {}
                    for opt in ['A', 'B', 'C', 'D', 'E']:
                        if row.get(opt) and row[opt].strip():
                            options[opt] = row[opt]
                    
                    # 检查题目是否已存在
                    qid = row['题号'].strip()
                    c.execute('SELECT id FROM questions WHERE id = ?', (qid,))
                    exists = c.fetchone()
                    
                    if exists:
                        # 更新现有题目
                        c.execute(
                            """UPDATE questions 
                               SET stem = ?, answer = ?, difficulty = ?, qtype = ?, 
                                   category = ?, options = ?
                               WHERE id = ?""",
                            (
                                row['题干'],
                                row['答案'],
                                row.get('难度', '无'),
                                row['题型'],
                                row.get('类别', '编程练习'),
                                json.dumps(options, ensure_ascii=False),
                                qid
                            )
                        )
                        updated_count += 1
                        print(f"✓ 更新题目: {qid}")
                    else:
                        # 插入新题目
                        c.execute(
                            """INSERT INTO questions 
                               (id, stem, answer, difficulty, qtype, category, options) 
                               VALUES (?,?,?,?,?,?,?)""",
                            (
                                qid,
                                row['题干'],
                                row['答案'],
                                row.get('难度', '无'),
                                row['题型'],
                                row.get('类别', '编程练习'),
                                json.dumps(options, ensure_ascii=False)
                            )
                        )
                        imported_count += 1
                        print(f"✓ 导入题目: {qid}")
                
                except Exception as e:
                    error_count += 1
                    print(f"✗ 错误处理题目 {row.get('题号', '未知')}: {e}")
        
        conn.commit()
        print(f"\n导入完成！")
        print(f"  新增题目: {imported_count}")
        print(f"  更新题目: {updated_count}")
        print(f"  错误数量: {error_count}")
        
        # 验证导入结果
        c.execute("SELECT COUNT(*) as cnt FROM questions WHERE qtype = '编程题'")
        total = c.fetchone()['cnt']
        print(f"\n数据库中编程题总数: {total}")
        
    except Exception as e:
        print(f"导入过程中发生错误: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("开始导入编程题...")
    print("=" * 50)
    import_coding_questions()
    print("=" * 50)
    print("导入脚本执行完成！")

