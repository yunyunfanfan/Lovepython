#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加需要输入的编程题到数据库
"""

import sqlite3
import json

def add_coding_questions():
    """添加编程题到数据库"""
    conn = sqlite3.connect('questions.db')
    c = conn.cursor()
    
    # 编程题列表
    coding_questions = [
        {
            'id': '10001',
            'stem': '编写程序，输入一个整数，输出它的平方。',
            'answer': '输入:5\n输出:25',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python基础',
            'options': json.dumps({
                '示例输入': '5',
                '示例输出': '25',
                '提示': '使用 input() 读取整数，使用 int() 转换'
            }, ensure_ascii=False)
        },
        {
            'id': '10002',
            'stem': '编写程序，输入两个整数（分两行输入），输出它们的和。',
            'answer': '输入:3,7\n输出:10',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python基础',
            'options': json.dumps({
                '示例输入': '3\n7',
                '示例输出': '10',
                '提示': '需要调用两次 input() 读取两个数字'
            }, ensure_ascii=False)
        },
        {
            'id': '10003',
            'stem': '编写程序，输入一个字符串，输出该字符串的长度。',
            'answer': '输入:Hello\n输出:5',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python字符串',
            'options': json.dumps({
                '示例输入': 'Hello',
                '示例输出': '5',
                '提示': '使用 len() 函数获取字符串长度'
            }, ensure_ascii=False)
        },
        {
            'id': '10004',
            'stem': '编写程序，输入一个整数n，输出1到n的和。例如输入5，输出15（1+2+3+4+5=15）。',
            'answer': '输入:5\n输出:15',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python基础',
            'options': json.dumps({
                '示例输入': '5',
                '示例输出': '15',
                '提示': '可以使用 sum(range(1, n+1)) 或循环累加'
            }, ensure_ascii=False)
        },
        {
            'id': '10005',
            'stem': '编写程序，输入三个整数（分三行输入），输出它们的平均值（保留两位小数）。',
            'answer': '输入:10,20,30\n输出:20.00',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python基础',
            'options': json.dumps({
                '示例输入': '10\n20\n30',
                '示例输出': '20.00',
                '提示': '使用 format() 或 f-string 格式化输出'
            }, ensure_ascii=False)
        },
        {
            'id': '10006',
            'stem': '编写程序，输入一个字符串，输出该字符串的反转结果。例如输入"hello"，输出"olleh"。',
            'answer': '输入:hello\n输出:olleh',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python字符串',
            'options': json.dumps({
                '示例输入': 'hello',
                '示例输出': 'olleh',
                '提示': '可以使用切片 [::-1] 或 reversed() 函数'
            }, ensure_ascii=False)
        },
        {
            'id': '10007',
            'stem': '编写程序，输入一个整数，判断它是奇数还是偶数。如果是奇数输出"odd"，如果是偶数输出"even"。',
            'answer': '输入:7\n输出:odd',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python条件控制',
            'options': json.dumps({
                '示例输入1': '7',
                '示例输出1': 'odd',
                '示例输入2': '8',
                '示例输出2': 'even',
                '提示': '使用 % 运算符判断是否能被2整除'
            }, ensure_ascii=False)
        },
        {
            'id': '10008',
            'stem': '编写程序，输入两个整数a和b，输出它们的最大值。',
            'answer': '输入:5,3\n输出:5',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python基础',
            'options': json.dumps({
                '示例输入': '5\n3',
                '示例输出': '5',
                '提示': '使用 max() 函数或 if-else 条件语句'
            }, ensure_ascii=False)
        },
        {
            'id': '10009',
            'stem': '编写程序，输入一个整数n，输出n的阶乘。例如输入5，输出120（5!=1*2*3*4*5=120）。',
            'answer': '输入:5\n输出:120',
            'difficulty': '中等',
            'qtype': '编程题',
            'category': 'Python基础',
            'options': json.dumps({
                '示例输入': '5',
                '示例输出': '120',
                '提示': '可以使用循环或递归实现阶乘'
            }, ensure_ascii=False)
        },
        {
            'id': '10010',
            'stem': '编写程序，输入一个整数n，判断它是否是质数。如果是质数输出"yes"，否则输出"no"。（质数是只能被1和自己整除的大于1的整数）',
            'answer': '输入:7\n输出:yes',
            'difficulty': '中等',
            'qtype': '编程题',
            'category': 'Python算法',
            'options': json.dumps({
                '示例输入1': '7',
                '示例输出1': 'yes',
                '示例输入2': '8',
                '示例输出2': 'no',
                '提示': '检查2到sqrt(n)之间是否有能整除n的数'
            }, ensure_ascii=False)
        },
        {
            'id': '10011',
            'stem': '编写程序，输入一个字符串，统计其中字母a出现的次数。',
            'answer': '输入:banana\n输出:3',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python字符串',
            'options': json.dumps({
                '示例输入': 'banana',
                '示例输出': '3',
                '提示': '使用 count() 方法或循环遍历'
            }, ensure_ascii=False)
        },
        {
            'id': '10012',
            'stem': '编写程序，输入一个整数n，输出斐波那契数列的第n项。斐波那契数列：0, 1, 1, 2, 3, 5, 8, 13...（第0项是0，第1项是1）',
            'answer': '输入:6\n输出:8',
            'difficulty': '中等',
            'qtype': '编程题',
            'category': 'Python算法',
            'options': json.dumps({
                '示例输入': '6',
                '示例输出': '8',
                '提示': 'F(0)=0, F(1)=1, F(n)=F(n-1)+F(n-2)'
            }, ensure_ascii=False)
        },
        {
            'id': '10013',
            'stem': '编写程序，输入一个整数n（n>=1），输出九九乘法表的第n行。例如输入3，输出"3x1=3 3x2=6 3x3=9"（用空格分隔）。',
            'answer': '输入:3\n输出:3x1=3 3x2=6 3x3=9',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python循环',
            'options': json.dumps({
                '示例输入': '3',
                '示例输出': '3x1=3 3x2=6 3x3=9',
                '提示': '使用循环输出，注意格式'
            }, ensure_ascii=False)
        },
        {
            'id': '10014',
            'stem': '编写程序，输入一个字符串，将其中的小写字母转换为大写，大写字母转换为小写。例如输入"Hello"，输出"hELLO"。',
            'answer': '输入:Hello\n输出:hELLO',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python字符串',
            'options': json.dumps({
                '示例输入': 'Hello',
                '示例输出': 'hELLO',
                '提示': '使用 swapcase() 方法或逐字符判断转换'
            }, ensure_ascii=False)
        },
        {
            'id': '10015',
            'stem': '编写程序，输入三个整数a、b、c（分三行输入），输出它们从小到大排序后的结果（用空格分隔）。',
            'answer': '输入:3,1,2\n输出:1 2 3',
            'difficulty': '简单',
            'qtype': '编程题',
            'category': 'Python基础',
            'options': json.dumps({
                '示例输入': '3\n1\n2',
                '示例输出': '1 2 3',
                '提示': '将三个数存入列表后使用 sorted() 排序'
            }, ensure_ascii=False)
        }
    ]
    
    # 插入题目
    added_count = 0
    skipped_count = 0
    
    for q in coding_questions:
        try:
            # 检查题目是否已存在
            c.execute('SELECT id FROM questions WHERE id = ?', (q['id'],))
            if c.fetchone():
                print(f"⚠️  题目 {q['id']} 已存在，跳过")
                skipped_count += 1
                continue
            
            # 插入新题目
            c.execute('''
                INSERT INTO questions (id, stem, answer, difficulty, qtype, category, options)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (q['id'], q['stem'], q['answer'], q['difficulty'], 
                  q['qtype'], q['category'], q['options']))
            
            print(f"✅ 添加题目 {q['id']}: {q['stem'][:30]}...")
            added_count += 1
            
        except Exception as e:
            print(f"❌ 添加题目 {q['id']} 失败: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"✨ 完成！共添加 {added_count} 道编程题")
    if skipped_count > 0:
        print(f"⚠️  跳过 {skipped_count} 道已存在的题目")
    print(f"{'='*50}")
    print(f"\n💡 题目ID范围：10001-10015")
    print(f"📚 分类包括：Python基础、Python字符串、Python条件控制、Python循环、Python算法")
    print(f"📝 难度分布：简单 {sum(1 for q in coding_questions if q['difficulty']=='简单')} 道，中等 {sum(1 for q in coding_questions if q['difficulty']=='中等')} 道")

if __name__ == '__main__':
    print("🚀 开始添加编程题到数据库...\n")
    add_coding_questions()
    print("\n✅ 所有操作完成！您现在可以在编程题模块中看到这些题目了。")


