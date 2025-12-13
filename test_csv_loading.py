#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CSV文件加载功能
"""

import sqlite3
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入app模块
from app import load_questions_to_db

def test_csv_loading():
    """测试CSV加载功能"""
    print("\n" + "="*60)
    print("🧪 测试 CSV 题库加载功能")
    print("="*60 + "\n")
    
    # 创建临时数据库连接
    conn = sqlite3.connect(':memory:')  # 使用内存数据库测试
    c = conn.cursor()
    
    # 创建questions表
    c.execute('''CREATE TABLE questions (
        id TEXT PRIMARY KEY,
        stem TEXT NOT NULL,
        answer TEXT NOT NULL,
        difficulty TEXT,
        qtype TEXT,
        category TEXT,
        options TEXT
    )''')
    conn.commit()
    
    print("✅ 测试数据库已创建\n")
    
    # 测试加载
    print("📥 开始加载 questions.csv...\n")
    result = load_questions_to_db(conn)
    
    print("\n" + "="*60)
    print("📊 加载结果报告")
    print("="*60)
    
    if result['success']:
        print(f"✅ 状态: 成功")
        print(f"📝 编码: {result['encoding_used']}")
        print(f"📚 题目数: {result['count']}")
        
        if result['errors']:
            print(f"⚠️  警告数: {len(result['errors'])}")
            print("\n前5个警告:")
            for i, error in enumerate(result['errors'][:5], 1):
                print(f"  {i}. {error}")
        else:
            print(f"✨ 无警告")
        
        # 显示样例题目
        print("\n" + "-"*60)
        print("📖 样例题目（前3题）")
        print("-"*60)
        
        c.execute('SELECT id, stem, answer, difficulty FROM questions LIMIT 3')
        for row in c.fetchall():
            print(f"\n题号: {row[0]}")
            print(f"题干: {row[1][:60]}...")
            print(f"答案: {row[2]}")
            print(f"难度: {row[3]}")
            
    else:
        print(f"❌ 状态: 失败")
        print(f"🚫 错误数: {len(result['errors'])}")
        print("\n错误详情:")
        for i, error in enumerate(result['errors'], 1):
            print(f"  {i}. {error}")
    
    print("\n" + "="*60 + "\n")
    
    conn.close()
    
    return result['success']

if __name__ == '__main__':
    success = test_csv_loading()
    sys.exit(0 if success else 1)
