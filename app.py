#!/usr/bin/env python3
"""
EXAM-MASTER - A Flask-based Online Quiz System

This application provides a complete quiz system with features including:
- User registration and authentication
- Question management with import from CSV
- Multiple quiz modes (random, sequential, timed, exam)
- User progress tracking and statistics
- Favorites, tags, and search functionality

Author: ShayneChen (xinyu-c@outlook.com)
License: MIT
"""

# Standard library imports
import csv
import json
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta
from functools import wraps

# Third-party imports
from flask import (
    Flask, 
    request, 
    render_template, 
    session, 
    redirect, 
    url_for, 
    flash, 
    jsonify, 
    abort,
    send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Import learning system module
from learning_system import (
    LearningSystem,
    QuestionManager,
    LearningProgressTracker,
    StatisticsAnalyzer,
    RecommendationEngine,
    CacheManager,
    AnalyzerFactory
)

# Initialize Flask application
app = Flask(__name__)
# Use environment variable for secret key with a fallback default
# In production, always set this through environment variables
app.secret_key = os.environ.get('SECRET_KEY', 'change_this_in_production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Static media directories for study resources
VIDEO_DIR = os.path.join(app.static_folder, 'videos')
DOC_DIR = os.path.join(app.static_folder, 'docs')

# Initialize Learning System (Singleton pattern)
learning_system = LearningSystem()

# Avatar upload configuration
ALLOWED_AVATAR_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

#############################
# Database Helper Functions #
#############################

def get_db():
    """
    Create a database connection and configure it to return rows as dictionaries.
    
    Returns:
        sqlite3.Connection: The configured database connection
    """
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initialize the database by creating necessary tables if they don't exist.
    Also loads initial question data from CSV if the questions table is empty.
    """
    conn = get_db()
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        current_seq_qid TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # History table for tracking user answers
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        user_answer TEXT NOT NULL,
        correct INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Questions table for storing question data
    c.execute('''CREATE TABLE IF NOT EXISTS questions (
        id TEXT PRIMARY KEY,
        stem TEXT NOT NULL,
        answer TEXT NOT NULL,
        difficulty TEXT,
        qtype TEXT,
        category TEXT,
        options TEXT, -- JSON stored options
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Favorites table for user bookmarks
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        tag TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, question_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (question_id) REFERENCES questions(id)
    )''')
    
    # Exam sessions table for timed mode and exams
    c.execute('''CREATE TABLE IF NOT EXISTS exam_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mode TEXT NOT NULL, -- 'exam' or 'timed'
        question_ids TEXT NOT NULL, -- JSON list
        start_time DATETIME NOT NULL,
        duration INTEGER NOT NULL, -- seconds
        completed BOOLEAN DEFAULT 0,
        score REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    conn.commit()

    # Load questions from CSV if the table is empty
    c.execute('SELECT COUNT(*) as cnt FROM questions')
    if c.fetchone()['cnt'] == 0:
        load_questions_to_db(conn)
    
    conn.close()

def load_questions_to_db(conn):
    """
    Load questions from a CSV file into the database.
    
    Args:
        conn (sqlite3.Connection): The database connection
    """
    try:
        with open('questions.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            c = conn.cursor()
            for row in reader:
                options = {}
                for opt in ['A', 'B', 'C', 'D', 'E']:
                    if row.get(opt) and row[opt].strip():
                        options[opt] = row[opt]
                c.execute(
                    "INSERT INTO questions (id, stem, answer, difficulty, qtype, category, options) VALUES (?,?,?,?,?,?,?)",
                    (
                        row["题号"],
                        row["题干"],
                        row["答案"],
                        row["难度"],
                        row["题型"],
                        row.get("类别", "未分类"),
                        json.dumps(options, ensure_ascii=False),
                    ),
                )
            conn.commit()
    except FileNotFoundError:
        print("Warning: questions.csv file not found. No questions loaded.")
    except Exception as e:
        print(f"Error loading questions: {e}")

# Initialize the database
init_db()

################################
# Authentication Helper Functions #
################################

def login_required(f):
    """
    Decorator to require login for a route.
    
    Args:
        f (function): The route function to decorate
        
    Returns:
        function: The decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash("请先登录后再访问该页面", "error")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def is_logged_in():
    """
    Check if the user is logged in.
    
    Returns:
        bool: True if user is logged in, False otherwise
    """
    return 'user_id' in session

def get_user_id():
    """
    Get the current user's ID from the session.
    
    Returns:
        int: The user ID if logged in, None otherwise
    """
    return session.get('user_id')

def list_media_files(directory, extensions):
    """
    Safely list files in a directory with given extensions.
    """
    if not os.path.isdir(directory):
        return []
    return sorted(
        [
            f
            for f in os.listdir(directory)
            if f.lower().endswith(tuple(ext.lower() for ext in extensions))
        ]
    )

##############################
# Question Helper Functions #
##############################

def fetch_question(qid):
    """
    Fetch a question by ID from the database.
    
    Args:
        qid (str): The question ID
        
    Returns:
        dict: The question data or None if not found
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM questions WHERE id=?', (qid,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row['id'],
            'stem': row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'category': row['category'],
            'options': json.loads(row['options'])
        }
    return None

def random_question_id(user_id):
    """
    Get a random question ID for a user, excluding questions they've already answered.
    
    Args:
        user_id (int): The user ID
        
    Returns:
        str: A random question ID or None if all questions have been answered
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id FROM questions 
        WHERE id NOT IN (
            SELECT question_id FROM history WHERE user_id=?
        )
        ORDER BY RANDOM() 
        LIMIT 1
    ''', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return row['id']
    return None

def fetch_random_question_ids(num):
    """
    Fetch multiple random question IDs.
    
    Args:
        num (int): The number of question IDs to fetch
        
    Returns:
        list: A list of random question IDs
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM questions ORDER BY RANDOM() LIMIT ?', (num,))
    rows = c.fetchall()
    conn.close()
    return [r['id'] for r in rows]

def is_favorite(user_id, question_id):
    """
    Check if a question is favorited by a user.
    
    Args:
        user_id (int): The user ID
        question_id (str): The question ID
        
    Returns:
        bool: True if favorited, False otherwise
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM favorites WHERE user_id=? AND question_id=?',
              (user_id, question_id))
    is_fav = bool(c.fetchone())
    conn.close()
    return is_fav

##############################
# Authentication Routes #
##############################

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Route for user registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Input validation
        if not username or not password:
            flash("用户名和密码不能为空", "error")
            return render_template('register.html')
            
        if password != confirm_password:
            flash("两次输入的密码不一致", "error")
            return render_template('register.html')
            
        if len(password) < 6:
            flash("密码长度不能少于6个字符", "error")
            return render_template('register.html')
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if username exists
        c.execute('SELECT id FROM users WHERE username=?', (username,))
        if c.fetchone():
            conn.close()
            flash("用户名已存在，请更换用户名", "error")
            return render_template('register.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        c.execute('INSERT INTO users (username, password_hash) VALUES (?,?)', 
                  (username, password_hash))
        conn.commit()
        conn.close()
        
        flash("注册成功，请登录", "success")
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Route for user login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("用户名和密码不能为空", "error")
            return render_template('login.html')
        
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, password_hash FROM users WHERE username=?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            
            # Redirect to 'next' parameter if provided
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
                
            return redirect(url_for('index'))
        else:
            flash("登录失败，用户名或密码错误", "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Route for user logout."""
    session.clear()
    flash("您已成功退出登录", "success")
    return redirect(url_for('login'))

##############################
# Profile / Account          #
##############################

def get_user_avatar_url(user_id):
    """Return the avatar url for the user if exists."""
    if not user_id:
        return None
    avatar_dir = os.path.join(app.static_folder, 'avatars')
    if not os.path.exists(avatar_dir):
        return None
    for ext in ALLOWED_AVATAR_EXTS:
        candidate = os.path.join(avatar_dir, f"user_{user_id}{ext}")
        if os.path.exists(candidate):
            return url_for('static', filename=f"avatars/user_{user_id}{ext}")
    return None


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT username, password_hash FROM users WHERE id=?', (user_id,))
    user = c.fetchone()
    current_username = user['username'] if user else ''
    password_hash = user['password_hash'] if user else ''

    message_type = None

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        avatar = request.files.get('avatar')
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Handle password change
        if current_password or new_password or confirm_password:
            if not current_password or not new_password or not confirm_password:
                flash("请完整填写当前密码、新密码和确认密码", "error")
            elif new_password != confirm_password:
                flash("两次输入的新密码不一致", "error")
            elif len(new_password) < 6:
                flash("新密码长度不能少于6个字符", "error")
            elif not user or not check_password_hash(password_hash, current_password):
                flash("当前密码不正确", "error")
            else:
                new_hash = generate_password_hash(new_password)
                c.execute('UPDATE users SET password_hash=? WHERE id=?', (new_hash, user_id))
                conn.commit()
                flash("密码已更新", "success")

        # Handle username change
        if new_username and new_username != current_username:
            # Check if username exists
            c.execute('SELECT id FROM users WHERE username=? AND id != ?', (new_username, user_id))
            exists = c.fetchone()
            if exists:
                flash("用户名已存在，请更换用户名", "error")
            else:
                c.execute('UPDATE users SET username=? WHERE id=?', (new_username, user_id))
                conn.commit()
                current_username = new_username
                flash("用户名已更新", "success")

        # Handle avatar upload
        if avatar and avatar.filename:
            filename = secure_filename(avatar.filename)
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext not in ALLOWED_AVATAR_EXTS:
                flash("头像格式不支持，请上传 png/jpg/jpeg/gif/webp", "error")
            else:
                avatar_dir = os.path.join(app.static_folder, 'avatars')
                os.makedirs(avatar_dir, exist_ok=True)
                save_path = os.path.join(avatar_dir, f"user_{user_id}{ext}")
                # 删除其他扩展的旧头像
                for old_ext in ALLOWED_AVATAR_EXTS:
                    old_path = os.path.join(avatar_dir, f"user_{user_id}{old_ext}")
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except Exception:
                            pass
                avatar.save(save_path)
                flash("头像已上传", "success")

    avatar_url = get_user_avatar_url(user_id)
    conn.close()

    return render_template('profile.html', username=current_username, avatar_url=avatar_url)

##############################
# Main Application Routes #
##############################

@app.route('/')
@login_required
def index():
    """Home page route."""
    # Fetch current sequential question ID if exists
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT current_seq_qid FROM users WHERE id = ?', (user_id,))
    user_data = c.fetchone()
    current_seq_qid = user_data['current_seq_qid'] if user_data and user_data['current_seq_qid'] else None
    conn.close()
    
    # Get intelligent recommendations
    recommendations = []
    try:
        recommendations_data = learning_system.get_recommendations(user_id, count=5)
        # Convert to list of question objects for display
        for rec in recommendations_data:
            question = learning_system.question_manager.get_question(rec['question_id'])
            if question:
                recommendations.append({
                    'question': question,
                    'score': rec['score'],
                    'reason': rec['reason'],
                    'priority': rec['priority']
                })
        
        # 如果没有推荐，提供一些随机题目作为默认推荐
        if not recommendations:
            all_questions = learning_system.question_manager._db_accessor.get_all_questions()
            if all_questions:
                # 获取用户已答题的ID
                conn = get_db()
                c = conn.cursor()
                c.execute('SELECT DISTINCT question_id FROM history WHERE user_id = ?', (user_id,))
                answered_ids = {row['question_id'] for row in c.fetchall()}
                conn.close()
                
                # 从未答题中随机选择5道
                unanswered = [q for q in all_questions if q.id not in answered_ids]
                if unanswered:
                    import random
                    random.shuffle(unanswered)
                    for question in unanswered[:5]:
                        recommendations.append({
                            'question': question,
                            'score': 50.0,
                            'reason': '系统为您推荐的新题目',
                            'priority': 2
                        })
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        import traceback
        traceback.print_exc()
        recommendations = []
    
    return render_template('index.html', 
                          current_year=datetime.now().year,
                          current_seq_qid=current_seq_qid,
                          recommendations=recommendations)

@app.route('/study')
@login_required
def study():
    """Learning hub entry page."""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT current_seq_qid FROM users WHERE id = ?', (user_id,))
    user_data = c.fetchone()

    # Basic progress overview for the current user
    c.execute('SELECT COUNT(*) as total FROM questions')
    total = c.fetchone()['total']
    c.execute('SELECT COUNT(DISTINCT question_id) as answered FROM history WHERE user_id=?', (user_id,))
    answered = c.fetchone()['answered']
    conn.close()

    current_seq_qid = user_data['current_seq_qid'] if user_data and user_data['current_seq_qid'] else None

    # Get intelligent recommendations
    recommendations = []
    try:
        recommendations_data = learning_system.get_recommendations(user_id, count=5)
        # Convert to list of question objects for display
        for rec in recommendations_data:
            question = learning_system.question_manager.get_question(rec['question_id'])
            if question:
                recommendations.append({
                    'question': question,
                    'score': rec['score'],
                    'reason': rec['reason'],
                    'priority': rec['priority']
                })
        
        # 如果没有推荐，提供一些随机题目作为默认推荐
        if not recommendations:
            all_questions = learning_system.question_manager._db_accessor.get_all_questions()
            if all_questions:
                # 获取用户已答题的ID
                conn = get_db()
                c = conn.cursor()
                c.execute('SELECT DISTINCT question_id FROM history WHERE user_id = ?', (user_id,))
                answered_ids = {row['question_id'] for row in c.fetchall()}
                conn.close()
                
                # 从未答题中随机选择5道
                unanswered = [q for q in all_questions if q.id not in answered_ids]
                if unanswered:
                    import random
                    random.shuffle(unanswered)
                    for question in unanswered[:5]:
                        recommendations.append({
                            'question': question,
                            'score': 50.0,
                            'reason': '系统为您推荐的新题目',
                            'priority': 2
                        })
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        import traceback
        traceback.print_exc()
        recommendations = []

    return render_template(
        'study.html',
        current_year=datetime.now().year,
        current_seq_qid=current_seq_qid,
        total=total,
        answered=answered,
        recommendations=recommendations
    )

@app.route('/study/video')
@login_required
def study_video():
    """Video learning hub."""
    videos = list_media_files(VIDEO_DIR, ['.mp4', '.webm', '.mov', '.m4v', '.ogg'])
    return render_template('study_video.html', videos=videos)

@app.route('/study/docs')
@login_required
def study_docs():
    """Document learning hub."""
    docs = list_media_files(DOC_DIR, ['.md'])
    selected = request.args.get('doc')
    content = None

    if selected and selected in docs:
        try:
            with open(os.path.join(DOC_DIR, selected), 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            flash(f"无法读取文档: {e}", "error")
            content = None
    elif selected and selected not in docs:
        flash("未找到该文档", "error")

    return render_template(
        'study_docs.html',
        docs=docs,
        selected_doc=selected,
        doc_content=content
    )

@app.route('/study/ai')
@login_required
def study_ai():
    """AI learning assistant placeholder page."""
    return render_template('study_ai.html')

@app.route('/study/coding')
@login_required
def study_coding():
    """Programming practice hub."""
    conn = get_db()
    c = conn.cursor()
    # 获取所有编程题（题型为"编程题"）
    c.execute("SELECT * FROM questions WHERE qtype = '编程题' OR qtype LIKE '%编程%' ORDER BY id")
    coding_questions = []
    for row in c.fetchall():
        coding_questions.append({
            'id': row['id'],
            'stem': row['stem'],
            'difficulty': row['difficulty'],
            'category': row['category']
        })
    conn.close()
    return render_template('study_coding.html', questions=coding_questions)

@app.route('/study/coding/<qid>', methods=['GET', 'POST'])
@login_required
def coding_question(qid):
    """Programming question page."""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM questions WHERE id = ?', (qid,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        flash("题目不存在", "error")
        return redirect(url_for('study_coding'))
    
    question = {
        'id': row['id'],
        'stem': row['stem'],
        'answer': row['answer'],  # 期望输出或测试用例
        'difficulty': row['difficulty'],
        'category': row['category'],
        'options': json.loads(row['options']) if row['options'] else {}
    }
    
    # 处理代码提交
    if request.method == 'POST':
        user_code = request.form.get('code', '').strip()
        
        if not user_code:
            flash("代码不能为空", "error")
            return render_template('coding_question.html', question=question)
        
        # 执行代码并判断
        result = execute_and_check_code(user_code, question['answer'])
        
        # 保存答题记录
        correct = 1 if result['correct'] else 0
        conn = get_db()
        c = conn.cursor()
        c.execute(
            'INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?,?,?,?)',
            (user_id, qid, user_code[:500], correct)  # 限制代码长度
        )
        conn.commit()
        conn.close()
        
        if result['correct']:
            flash("恭喜！代码运行正确！", "success")
        else:
            flash(f"代码运行有误：{result['error']}", "error")
        
        return render_template('coding_question.html', 
                             question=question, 
                             user_code=user_code,
                             result=result)
    
    return render_template('coding_question.html', question=question)

def execute_and_check_code(user_code, expected_output):
    """
    安全执行用户代码并判断是否正确
    
    Args:
        user_code: 用户提交的代码
        expected_output: 期望输出（可以是输出字符串或测试用例）
    
    Returns:
        dict: 包含执行结果和判断结果
    """
    import subprocess
    import sys
    import tempfile
    import os
    import re
    
    result = {
        'correct': False,
        'output': '',
        'error': '',
        'execution_time': 0
    }
    
    # 安全检查：禁止危险操作
    dangerous_keywords = ['import os', 'import sys', '__import__', 'eval', 'exec', 
                          'open(', 'file(', 'input(', 'raw_input', 'subprocess',
                          'compile(', 'reload(', '__builtins__']
    
    code_lower = user_code.lower()
    for keyword in dangerous_keywords:
        if keyword.lower() in code_lower:
            result['error'] = f'代码包含不允许的操作：{keyword}'
            return result
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(user_code)
            temp_file = f.name
        
        try:
            # 执行代码，限制时间和资源
            start_time = time.time()
            process = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=5,  # 5秒超时
                cwd=tempfile.gettempdir(),
                env={**os.environ, 'PYTHONPATH': ''}  # 限制Python路径
            )
            execution_time = time.time() - start_time
            
            result['execution_time'] = execution_time
            result['output'] = process.stdout.strip()
            
            if process.returncode != 0:
                error_msg = process.stderr.strip() or '代码执行出错'
                # 简化错误信息，移除文件路径
                error_msg = re.sub(r'File "[^"]+", line \d+', '代码', error_msg)
                result['error'] = error_msg
                return result
            
            # 判断输出是否正确
            # 如果expected_output是测试用例格式（如：输入:1,2 输出:3），需要解析
            expected = expected_output.strip()
            if '输出:' in expected or '输出：' in expected:
                # 提取期望输出
                if '输出:' in expected:
                    expected = expected.split('输出:')[1].strip()
                else:
                    expected = expected.split('输出：')[1].strip()
            
            # 比较输出（去除首尾空白，支持多行）
            actual_output = result['output'].strip()
            expected_output_clean = expected.strip()
            
            # 支持多行输出比较
            result['correct'] = (actual_output == expected_output_clean)
            
            if not result['correct']:
                result['error'] = f"期望输出：\n{expected_output_clean}\n\n实际输出：\n{actual_output}"
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        result['error'] = '代码执行超时（超过5秒），请优化代码性能'
    except Exception as e:
        result['error'] = f'执行错误：{str(e)}'
    
    return result

@app.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    """API endpoint for AI chat."""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'error': '消息不能为空'
            }), 400
        
        # 智谱AI (BigModel) API Key
        # 优先从环境变量获取，否则使用默认值
        api_key = os.environ.get('AI_API_KEY', 'a071b0cb84ce4f8a9057f78aa6e40f6c.tPmpuASAkobJJ7WV')
        
        import requests
        
        # 智谱AI API 配置（根据官方文档）
        # API端点：https://open.bigmodel.cn/api/paas/v4/chat/completions
        api_url = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 构建提示词，专注于 Python 学习
        system_prompt = """你是一个专业的 Python 学习助手，擅长：
1. 解释 Python 语法和概念
2. 解答编程问题
3. 提供学习建议和练习题目
4. 帮助调试代码错误

请用中文回答，语言简洁明了，适合初学者理解。"""
        
        # 智谱AI API 请求格式（根据官方文档）
        # 免费模型列表（按优先级排序）
        free_models = ['glm-4-flash', 'glm-4', 'chatglm3-6b']
        
        # 尝试每个模型，直到成功
        last_error = None
        for model_name in free_models:
            payload = {
                'model': model_name,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': message}
                ],
                'temperature': 1.0,  # 根据官方文档示例
                'max_tokens': 2048
            }
            
            # 调用智谱AI API
            try:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 智谱AI 响应格式与 OpenAI 兼容
                    if 'choices' in result and len(result['choices']) > 0:
                        ai_response = result['choices'][0]['message']['content']
                        return jsonify({
                            'success': True,
                            'response': ai_response,
                            'model_used': model_name  # 返回使用的模型名称
                        })
                    else:
                        last_error = 'AI 返回格式异常'
                        continue  # 尝试下一个模型
                else:
                    # 记录错误，尝试下一个模型
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('error', {}).get('message', error_detail)
                    except:
                        pass
                    last_error = f'模型 {model_name} 调用失败: {error_detail}'
                    # 如果是模型不存在错误，继续尝试下一个
                    if response.status_code == 400 and '模型' in error_detail:
                        continue
                    # 其他错误也继续尝试
                    continue
                    
            except requests.exceptions.Timeout:
                last_error = f'模型 {model_name} 响应超时'
                continue  # 尝试下一个模型
            except requests.exceptions.RequestException as e:
                last_error = f'模型 {model_name} 网络错误: {str(e)}'
                continue  # 尝试下一个模型
        
        # 所有模型都失败了
        return jsonify({
            'success': False,
            'error': '所有免费模型都不可用',
            'detail': last_error or '请检查 API key 和网络连接'
        }), 500
            
    except Exception as e:
        print(f"Error in ai_chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/reset_history', methods=['POST'])
@login_required
def reset_history():
    """Route to reset a user's answer history."""
    user_id = get_user_id()
    
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM history WHERE user_id=?', (user_id,))
        # Also clear the current sequential question ID
        c.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        flash("答题历史已重置。现在您可以重新开始答题。", "success")
    except Exception as e:
        flash(f"重置历史时出错: {str(e)}", "error")
        
    return redirect(url_for('random_question'))

##############################
# Question Routes #
##############################

@app.route('/random', methods=['GET'])
@login_required
def random_question():
    """Route to get a random question."""
    user_id = get_user_id()
    qid = random_question_id(user_id)
    
    conn = get_db()
    c = conn.cursor()
    # Get total questions count
    c.execute('SELECT COUNT(*) as total FROM questions')
    total = c.fetchone()['total']
    # Get answered questions count
    c.execute('SELECT COUNT(DISTINCT question_id) as answered FROM history WHERE user_id=?', (user_id,))
    answered = c.fetchone()['answered']
    conn.close()
    
    if not qid:
        flash("您已完成所有题目！可以重置历史以重新开始。", "info")
        return render_template('question.html', question=None, answered=answered, total=total)
        
    q = fetch_question(qid)
    is_fav = is_favorite(user_id, qid)
    
    return render_template('question.html', 
                          question=q, 
                          answered=answered, 
                          total=total,
                          is_favorite=is_fav)

@app.route('/question/<qid>', methods=['GET', 'POST'])
@login_required
def show_question(qid):
    """Route to view and answer a specific question."""
    user_id = get_user_id()
    q = fetch_question(qid)
    
    if q is None:
        flash("题目不存在", "error")
        return redirect(url_for('index'))

    # Update last browsed question when viewing any question
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (qid, user_id))
    conn.commit()

    # Handle form submission (answer)
    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = "".join(sorted(user_answer))
        correct = int(user_answer_str == "".join(sorted(q['answer'])))

        # Save answer to history
        c.execute(
            'INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?,?,?,?)',
            (user_id, qid, user_answer_str, correct)
        )
        conn.commit()

        # Get updated stats
        c.execute('SELECT COUNT(*) AS total FROM questions')
        total = c.fetchone()['total']
        c.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id=?', (user_id,))
        answered = c.fetchone()['answered']
        conn.close()

        result_msg = "回答正确" if correct else f"回答错误，正确答案：{q['answer']}"
        flash(result_msg, "success" if correct else "error")
        
        is_fav = is_favorite(user_id, qid)
        
        return render_template('question.html',
                              question=q,
                              result_msg=result_msg,
                              answered=answered,
                              total=total,
                              is_favorite=is_fav)

    # Handle GET request
    c.execute('SELECT COUNT(*) AS total FROM questions')
    total = c.fetchone()['total']
    c.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id=?', (user_id,))
    answered = c.fetchone()['answered']
    conn.close()
    
    is_fav = is_favorite(user_id, qid)

    return render_template('question.html',
                          question=q,
                          answered=answered,
                          total=total,
                          is_favorite=is_fav)

@app.route('/history')
@login_required
def show_history():
    """Route to view answer history."""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM history WHERE user_id=? ORDER BY timestamp DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    history_data = []
    for r in rows:
        q = fetch_question(r['question_id'])
        stem = q['stem'] if q else '题目已删除'
        history_data.append({
            'id': r['id'],
            'question_id': r['question_id'],
            'stem': stem,
            'user_answer': r['user_answer'],
            'correct': r['correct'],
            'timestamp': r['timestamp']
        })
    
    return render_template('history.html', history=history_data)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Route to search for questions by keyword."""
    query = request.form.get('query', '')
    results = []
    
    if query:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM questions WHERE stem LIKE ?", ('%'+query+'%',))
        rows = c.fetchall()
        conn.close()
        
        for row in rows:
            q = {
                'id': row['id'],
                'stem': row['stem']
            }
            results.append(q)
    
    return render_template('search.html', query=query, results=results)

@app.route('/wrong')
@login_required
def wrong_questions():
    """Route to view wrong answers."""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT question_id FROM history WHERE user_id=? AND correct=0', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    wrong_ids = set(r['question_id'] for r in rows)
    questions_list = []
    
    for qid in wrong_ids:
        q = fetch_question(qid)
        if q:
            questions_list.append(q)
    
    return render_template('wrong.html', questions=questions_list)

@app.route('/only_wrong')
@login_required
def only_wrong_mode():
    """Route to practice only wrong questions."""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT question_id FROM history WHERE user_id=? AND correct=0', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    wrong_ids = [r['question_id'] for r in rows]
    
    if not wrong_ids:
        flash("你没有错题或还未答题", "info")
        return redirect(url_for('index'))
    
    qid = random.choice(wrong_ids)
    q = fetch_question(qid)
    is_fav = is_favorite(user_id, qid)
    
    return render_template('question.html', 
                          question=q, 
                          is_favorite=is_fav)

##############################
# Browse Routes #
##############################

@app.route('/browse')
@login_required
def browse_questions():
    """Route to browse all questions."""
    user_id = get_user_id()
    page = request.args.get('page', 1, type=int)
    question_type = request.args.get('type', '')
    search_query = request.args.get('search', '')
    per_page = 20  # Questions per page
    
    conn = get_db()
    c = conn.cursor()
    
    # Build SQL query with filters
    where_conditions = []
    params = []
    
    if question_type and question_type != 'all':
        where_conditions.append('qtype = ?')
        params.append(question_type)
    
    if search_query:
        where_conditions.append('(stem LIKE ? OR id LIKE ?)')
        params.extend(['%' + search_query + '%', '%' + search_query + '%'])
    
    where_clause = ' WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
    
    # Get total count with filters
    count_sql = f'SELECT COUNT(*) as total FROM questions{where_clause}'
    c.execute(count_sql, params)
    total = c.fetchone()['total']
    
    # Get questions with pagination and filters
    offset = (page - 1) * per_page
    query_params = params + [per_page, offset]
    c.execute(f'''
        SELECT id, stem, answer, difficulty, qtype, category, options 
        FROM questions 
        {where_clause}
        ORDER BY CAST(id AS INTEGER) ASC 
        LIMIT ? OFFSET ?
    ''', query_params)
    
    rows = c.fetchall()
    questions = []
    
    for row in rows:
        question_data = {
            'id': row['id'],
            'stem': row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'category': row['category'],
            'options': json.loads(row['options']) if row['options'] else {}
        }
        
        # Check if favorited by current user
        c.execute('SELECT 1 FROM favorites WHERE user_id=? AND question_id=?', 
                  (user_id, row['id']))
        question_data['is_favorite'] = bool(c.fetchone())
        
        questions.append(question_data)
    
    # Get available question types for filter chips
    c.execute('SELECT DISTINCT qtype FROM questions WHERE qtype IS NOT NULL AND qtype != ""')
    available_types = [r['qtype'] for r in c.fetchall()]
    
    conn.close()
    
    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template('browse.html',
                          questions=questions,
                          total=total,
                          page=page,
                          per_page=per_page,
                          total_pages=total_pages,
                          has_prev=has_prev,
                          has_next=has_next,
                          current_type=question_type,
                          current_search=search_query,
                          available_types=available_types)

##############################
# Filter Routes #
##############################

@app.route('/filter', methods=['GET', 'POST'])
@login_required
def filter_questions():
    """Route to filter questions by category and difficulty."""
    conn = get_db()
    c = conn.cursor()
    
    # Get all categories and difficulties for dropdown selection
    c.execute('SELECT DISTINCT category FROM questions WHERE category IS NOT NULL AND category != ""')
    categories = [r['category'] for r in c.fetchall()]
    
    c.execute('SELECT DISTINCT difficulty FROM questions WHERE difficulty IS NOT NULL AND difficulty != ""')
    difficulties = [r['difficulty'] for r in c.fetchall()]

    selected_category = ''
    selected_difficulty = ''
    results = []
    
    if request.method == 'POST':
        selected_category = request.form.get('category', '')
        selected_difficulty = request.form.get('difficulty', '')
        
        sql = "SELECT id, stem FROM questions WHERE 1=1"
        params = []
        
        if selected_category:
            sql += " AND category=?"
            params.append(selected_category)
            
        if selected_difficulty:
            sql += " AND difficulty=?"
            params.append(selected_difficulty)
            
        c.execute(sql, params)
        rows = c.fetchall()
        
        for row in rows:
            results.append({'id': row['id'], 'stem': row['stem']})

    conn.close()
    
    return render_template('filter.html', 
                          categories=categories, 
                          difficulties=difficulties,
                          selected_category=selected_category,
                          selected_difficulty=selected_difficulty,
                          results=results)

##############################
# Favorites Routes #
##############################

@app.route('/favorite/<qid>', methods=['POST'])
@login_required
def favorite_question(qid):
    """Route to add a question to favorites."""
    user_id = get_user_id()
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('INSERT OR IGNORE INTO favorites (user_id, question_id, tag) VALUES (?,?,?)',
                  (user_id, qid, ''))
        conn.commit()
        flash("收藏成功！", "success")
    except Exception as e:
        flash(f"收藏失败: {str(e)}", "error")
    finally:
        conn.close()
    
    # Redirect back to the question page
    referrer = request.referrer
    if referrer and '/question/' in referrer:
        return redirect(referrer)
    return redirect(url_for('show_question', qid=qid))

@app.route('/unfavorite/<qid>', methods=['POST'])
@login_required
def unfavorite_question(qid):
    """Route to remove a question from favorites."""
    user_id = get_user_id()
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('DELETE FROM favorites WHERE user_id=? AND question_id=?', 
                  (user_id, qid))
        conn.commit()
        flash("已取消收藏", "success")
    except Exception as e:
        flash(f"取消收藏失败: {str(e)}", "error")
    finally:
        conn.close()
    
    # Redirect back to the question page
    referrer = request.referrer
    if referrer and '/question/' in referrer:
        return redirect(referrer)
    return redirect(url_for('show_question', qid=qid))

@app.route('/update_tag/<qid>', methods=['POST'])
@login_required
def update_tag(qid):
    """API route to update a favorite's tag."""
    if not is_logged_in():
        return jsonify({"success": False, "msg": "未登录"}), 401
    
    user_id = get_user_id()
    new_tag = request.form.get('tag', '')
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('UPDATE favorites SET tag=? WHERE user_id=? AND question_id=?',
                  (new_tag, user_id, qid))
        conn.commit()
        return jsonify({"success": True, "msg": "标记更新成功"})
    except Exception as e:
        return jsonify({"success": False, "msg": f"更新失败: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/favorites')
@login_required
def show_favorites():
    """Route to view favorites."""
    user_id = get_user_id()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT f.question_id, f.tag, q.stem 
        FROM favorites f 
        JOIN questions q ON f.question_id=q.id 
        WHERE f.user_id=?
    ''', (user_id,))
    
    rows = c.fetchall()
    conn.close()
    
    favorites_data = [
        {'question_id': r['question_id'], 'tag': r['tag'], 'stem': r['stem']} 
        for r in rows
    ]
    
    return render_template('favorites.html', favorites=favorites_data)

##############################
# Sequential Mode Routes #
##############################

@app.route('/sequential_start')
@login_required
def sequential_start():
    """Route to start or continue sequential answering mode."""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()

    # Check if user has a saved position
    c.execute('SELECT current_seq_qid FROM users WHERE id=?', (user_id,))
    user_data = c.fetchone()
    
    if user_data and user_data['current_seq_qid']:
        # Continue from last browsed position (start from where user left off)
        current_qid = user_data['current_seq_qid']
    else:
        # Find the first unanswered question
        c.execute('''
            SELECT id
            FROM questions
            WHERE id NOT IN (
                SELECT question_id FROM history WHERE user_id = ?
            )
            ORDER BY CAST(id AS INTEGER) ASC
            LIMIT 1
        ''', (user_id,))
        row = c.fetchone()
        
        if row is None:
            # If all questions are answered, find the first question
            c.execute('''
                SELECT id
                FROM questions
                ORDER BY CAST(id AS INTEGER) ASC
                LIMIT 1
            ''')
            row = c.fetchone()
            
            if row is None:
                conn.close()
                flash("题库中没有题目！", "error")
                return redirect(url_for('index'))
            
            current_qid = row['id']
            flash("所有题目已完成，从第一题重新开始。", "info")
        else:
            current_qid = row['id']
        
        # Save the position
        c.execute(
            'UPDATE users SET current_seq_qid = ? WHERE id = ?',
            (current_qid, user_id)
        )
        conn.commit()
    
    conn.close()
    return redirect(url_for('show_sequential_question', qid=current_qid))

@app.route('/sequential/<qid>', methods=['GET', 'POST'])
@login_required
def show_sequential_question(qid):
    """Route to show and handle sequential questions."""
    user_id = get_user_id()
    q = fetch_question(qid)
    
    if q is None:
        flash("题目不存在", "error")
        return redirect(url_for('index'))

    next_qid = None
    result_msg = None
    user_answer_str = ""
    
    conn = get_db()
    c = conn.cursor()
    
    # Update current_seq_qid to the current question when viewing it
    c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (qid, user_id))
    conn.commit()
    
    # Handle POST request (user submitted an answer)
    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = "".join(sorted(user_answer))
        correct = int(user_answer_str == "".join(sorted(q['answer'])))
        
        # Save answer to history
        c.execute('INSERT INTO history (user_id, question_id, user_answer, correct) '
                  'VALUES (?,?,?,?)',
                  (user_id, qid, user_answer_str, correct))
        
        # Find next unanswered question with higher ID
        c.execute('''
            SELECT id FROM questions
            WHERE CAST(id AS INTEGER) > ?
              AND id NOT IN (
                  SELECT question_id FROM history WHERE user_id = ?
              )
            ORDER BY CAST(id AS INTEGER) ASC
            LIMIT 1
        ''', (int(qid), user_id))
        
        row = c.fetchone()
        if row:
            next_qid = row['id']
            c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?',
                      (next_qid, user_id))
        else:
            # Check if there are any questions left to answer
            c.execute('''
                SELECT id FROM questions
                WHERE id NOT IN (
                    SELECT question_id FROM history WHERE user_id = ?
                )
                ORDER BY CAST(id AS INTEGER) ASC
                LIMIT 1
            ''', (user_id,))
            
            row = c.fetchone()
            if row:
                next_qid = row['id']
                c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?',
                          (next_qid, user_id))
            else:
                # All questions answered, reset to first question
                c.execute('''
                    SELECT id FROM questions
                    ORDER BY CAST(id AS INTEGER) ASC
                    LIMIT 1
                ''')
                row = c.fetchone()
                if row:
                    next_qid = row['id']
                    c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?',
                              (next_qid, user_id))
                    flash("所有题目已完成，从第一题重新开始。", "info")
                else:
                    c.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?',
                              (user_id,))
            
        result_msg = "回答正确！" if correct else f"回答错误，正确答案：{q['answer']}"
        flash(result_msg, "success" if correct else "error")
    
    # Get progress statistics
    c.execute('SELECT COUNT(*) AS total FROM questions')
    total = c.fetchone()['total']
    
    c.execute('SELECT COUNT(DISTINCT question_id) AS answered '
              'FROM history WHERE user_id = ?', (user_id,))
    answered = c.fetchone()['answered']
    
    conn.commit()
    conn.close()
    
    is_fav = is_favorite(user_id, qid)
    
    return render_template('question.html',
                          question=q,
                          result_msg=result_msg,
                          next_qid=next_qid,
                          sequential_mode=True,
                          user_answer=user_answer_str,
                          answered=answered,
                          total=total,
                          is_favorite=is_fav)

##############################
# Timed Mode & Exam Routes #
##############################

@app.route('/modes')
@login_required
def modes():
    """Route to select quiz mode."""
    return render_template('index.html', mode_select=True, current_year=datetime.now().year)

@app.route('/start_timed_mode', methods=['POST'])
@login_required
def start_timed_mode():
    """Route to start timed mode quiz."""
    user_id = get_user_id()
    
    # Configuration for timed mode
    question_count = int(request.form.get('question_count', 5))
    duration_minutes = int(request.form.get('duration', 10))
    
    question_ids = fetch_random_question_ids(question_count)
    start_time = datetime.now()
    duration = duration_minutes * 60  # Convert minutes to seconds
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO exam_sessions 
            (user_id, mode, question_ids, start_time, duration) 
            VALUES (?,?,?,?,?)
        ''', (user_id, 'timed', json.dumps(question_ids), start_time, duration))
        
        exam_id = c.lastrowid
        conn.commit()
        session['current_exam_id'] = exam_id
        
        return redirect(url_for('timed_mode'))
    except Exception as e:
        flash(f"启动定时模式失败: {str(e)}", "error")
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/timed_mode')
@login_required
def timed_mode():
    """Route for timed mode quiz interface."""
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        flash("未启动定时模式", "error")
        return redirect(url_for('index'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = c.fetchone()
    conn.close()
    
    if not exam:
        flash("无法找到考试会话", "error")
        return redirect(url_for('index'))
    
    question_ids = json.loads(exam['question_ids'])
    start_time = datetime.strptime(exam['start_time'], '%Y-%m-%d %H:%M:%S.%f')
    end_time = start_time + timedelta(seconds=exam['duration'])
    
    remaining = (end_time - datetime.now()).total_seconds()
    if remaining <= 0:
        # Time's up, auto-submit
        return redirect(url_for('submit_timed_mode'))
    
    questions_list = [fetch_question(qid) for qid in question_ids]
    return render_template('timed_mode.html', questions=questions_list, remaining=remaining)

@app.route('/submit_timed_mode', methods=['POST', 'GET'])
@login_required
def submit_timed_mode():
    """Route to submit answers from timed mode."""
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        flash("没有正在进行的定时模式", "error")
        return redirect(url_for('index'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = c.fetchone()
    
    if not exam:
        conn.close()
        flash("无法找到考试会话", "error")
        return redirect(url_for('index'))
    
    question_ids = json.loads(exam['question_ids'])
    
    # Process answers
    correct_count = 0
    total = len(question_ids)
    
    for qid in question_ids:
        user_answer = request.form.getlist(f'answer_{qid}')
        q = fetch_question(qid)
        
        if not q:
            continue
            
        user_answer_str = "".join(sorted(user_answer))
        correct = 1 if user_answer_str == "".join(sorted(q['answer'])) else 0
        
        if correct:
            correct_count += 1
            
        # Save to history
        c.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?,?,?,?)',
                  (user_id, qid, user_answer_str, correct))
    
    # Mark session as completed and save score
    score = (correct_count / total * 100) if total > 0 else 0
    c.execute('UPDATE exam_sessions SET completed=1, score=? WHERE id=?', (score, exam_id))
    conn.commit()
    conn.close()
    
    # Clear session
    session.pop('current_exam_id', None)
    
    flash(f"定时模式结束！正确率：{correct_count}/{total} = {score:.2f}%", 
          "success" if score >= 60 else "error")
    
    return redirect(url_for('statistics'))

@app.route('/start_exam', methods=['POST'])
@login_required
def start_exam():
    """Route to start exam mode."""
    user_id = get_user_id()
    
    # Configuration
    question_count = int(request.form.get('question_count', 10))
    
    question_ids = fetch_random_question_ids(question_count)
    start_time = datetime.now()
    duration = 0  # 0 means no time limit
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO exam_sessions 
            (user_id, mode, question_ids, start_time, duration) 
            VALUES (?,?,?,?,?)
        ''', (user_id, 'exam', json.dumps(question_ids), start_time, duration))
        
        exam_id = c.lastrowid
        conn.commit()
        session['current_exam_id'] = exam_id
        
        return redirect(url_for('exam'))
    except Exception as e:
        flash(f"启动模拟考试失败: {str(e)}", "error")
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/exam')
@login_required
def exam():
    """Route for exam mode interface."""
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        flash("未启动考试模式", "error")
        return redirect(url_for('index'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = c.fetchone()
    conn.close()
    
    if not exam:
        flash("无法找到考试", "error")
        return redirect(url_for('index'))
    
    question_ids = json.loads(exam['question_ids'])
    questions_list = [fetch_question(qid) for qid in question_ids]
    
    return render_template('exam.html', questions=questions_list)

@app.route('/submit_exam', methods=['POST'])
@login_required
def submit_exam():
    """Route to submit answers from exam mode."""
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        return jsonify({
            "success": False,
            "msg": "没有正在进行的考试"
        }), 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = c.fetchone()
    
    if not exam:
        conn.close()
        return jsonify({
            "success": False,
            "msg": "无法找到考试"
        }), 404
    
    question_ids = json.loads(exam['question_ids'])
    
    # Process answers
    correct_count = 0
    total = len(question_ids)
    question_results = []
    
    for qid in question_ids:
        user_answer = request.form.getlist(f'answer_{qid}')
        q = fetch_question(qid)
        
        if not q:
            continue
            
        user_answer_str = "".join(sorted(user_answer))
        correct = 1 if user_answer_str == "".join(sorted(q['answer'])) else 0
        
        if correct:
            correct_count += 1
            
        # Save to history
        c.execute('INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?,?,?,?)',
                  (user_id, qid, user_answer_str, correct))
        
        # Add to results
        question_results.append({
            "id": qid,
            "stem": q['stem'],
            "user_answer": user_answer_str,
            "correct_answer": q['answer'],
            "is_correct": correct == 1
        })
    
    # Mark session as completed and save score
    score = (correct_count / total * 100) if total > 0 else 0
    c.execute('UPDATE exam_sessions SET completed=1, score=? WHERE id=?', (score, exam_id))
    conn.commit()
    conn.close()
    
    # Clear session
    session.pop('current_exam_id', None)
    
    # Return detailed results
    return jsonify({
        "success": True,
        "correct_count": correct_count,
        "total": total,
        "score": score,
        "results": question_results
    })

##############################
# Statistics Routes #
##############################

@app.route('/statistics')
@login_required
def statistics():
    """Route to view user statistics."""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    
    # Overall accuracy
    c.execute('''
        SELECT 
            COUNT(*) as total, 
            SUM(correct) as correct_count 
        FROM history 
        WHERE user_id=?
    ''', (user_id,))
    
    row = c.fetchone()
    total = row['total'] if row['total'] else 0
    correct_count = row['correct_count'] if row['correct_count'] else 0
    overall_accuracy = (correct_count/total*100) if total>0 else 0
    
    # Stats by difficulty
    c.execute('''
        SELECT 
            q.difficulty, 
            COUNT(*) as total, 
            SUM(h.correct) as correct_count
        FROM history h 
        JOIN questions q ON h.question_id=q.id
        WHERE h.user_id=?
        GROUP BY q.difficulty
    ''', (user_id,))
    
    difficulty_stats = []
    for r in c.fetchall():
        difficulty_stats.append({
            'difficulty': r['difficulty'] or '未分类',
            'total': r['total'],
            'correct_count': r['correct_count'],
            'accuracy': (r['correct_count']/r['total']*100) if r['total']>0 else 0
        })
    
    # Stats by category
    c.execute('''
        SELECT 
            q.category, 
            COUNT(*) as total, 
            SUM(h.correct) as correct_count
        FROM history h 
        JOIN questions q ON h.question_id=q.id
        WHERE h.user_id=?
        GROUP BY q.category
    ''', (user_id,))
    
    category_stats = []
    for r in c.fetchall():
        category_stats.append({
            'category': r['category'] or '未分类',
            'total': r['total'],
            'correct_count': r['correct_count'],
            'accuracy': (r['correct_count']/r['total']*100) if r['total']>0 else 0
        })
    
    # Most wrong questions
    c.execute('''
        SELECT 
            h.question_id, 
            COUNT(*) as wrong_times, 
            q.stem
        FROM history h 
        JOIN questions q ON h.question_id=q.id
        WHERE h.user_id=? AND h.correct=0
        GROUP BY h.question_id
        ORDER BY wrong_times DESC
        LIMIT 10
    ''', (user_id,))
    
    worst_questions = []
    for r in c.fetchall():
        worst_questions.append({
            'question_id': r['question_id'],
            'stem': r['stem'],
            'wrong_times': r['wrong_times']
        })
    
    # Recent exams
    c.execute('''
        SELECT 
            id, 
            mode, 
            start_time, 
            score, 
            (SELECT COUNT(*) FROM JSON_EACH(question_ids)) as question_count
        FROM exam_sessions
        WHERE user_id=? AND completed=1
        ORDER BY start_time DESC
        LIMIT 5
    ''', (user_id,))
    
    recent_exams = []
    for r in c.fetchall():
        recent_exams.append({
            'id': r['id'],
            'mode': r['mode'],
            'start_time': r['start_time'],
            'score': r['score'],
            'question_count': r['question_count']
        })
    
    conn.close()
    
    return render_template('statistics.html', 
                          overall_accuracy=overall_accuracy,
                          difficulty_stats=difficulty_stats,
                          category_stats=category_stats,
                          worst_questions=worst_questions,
                          recent_exams=recent_exams)

##############################
# Learning System API Routes #
##############################

@app.route('/api/recommendations')
@login_required
def get_recommendations():
    """API endpoint to get question recommendations."""
    user_id = get_user_id()
    count = request.args.get('count', 10, type=int)
    
    try:
        recommendations = learning_system.get_recommendations(user_id, count)
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/wrong_recommendations')
@login_required
def get_wrong_recommendations():
    """API endpoint to get wrong question recommendations."""
    user_id = get_user_id()
    count = request.args.get('count', 5, type=int)
    
    try:
        recommendations = learning_system.get_wrong_question_recommendations(user_id, count)
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    except Exception as e:
        print(f"Error getting wrong recommendations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/learning_progress')
@login_required
def get_learning_progress():
    """API endpoint to get learning progress."""
    user_id = get_user_id()
    
    try:
        progress = learning_system.get_user_progress(user_id)
        return jsonify({
            'success': True,
            'progress': progress
        })
    except Exception as e:
        print(f"Error getting learning progress: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/learning_trend')
@login_required
def get_learning_trend():
    """API endpoint to get learning trend."""
    user_id = get_user_id()
    days = request.args.get('days', 7, type=int)
    
    try:
        progress_tracker = LearningProgressTracker(
            learning_system.db_accessor,
            learning_system.question_manager
        )
        trend = progress_tracker.get_learning_trend(user_id, days)
        return jsonify({
            'success': True,
            'trend': trend
        })
    except Exception as e:
        print(f"Error getting learning trend: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cache_stats')
@login_required
def get_cache_stats():
    """API endpoint to get cache statistics."""
    try:
        stats = learning_system.cache_manager.get_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

##############################
# APK Download Routes #
##############################

@app.route('/ExamMasterAndroid/<filename>')
def download_apk(filename):
    """Handle APK file downloads."""
    try:
        # Security check: only allow .apk files
        if not filename.endswith('.apk'):
            abort(404)
        
        # Use absolute path based on script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        apk_path = os.path.join(script_dir, 'ExamMasterAndroid', filename)
        
        # Check if file exists
        if not os.path.exists(apk_path):
            abort(404)
        
        # Send file with proper headers
        return send_file(
            apk_path, 
            as_attachment=True, 
            download_name=filename,
            mimetype='application/vnd.android.package-archive'
        )
        
    except Exception as e:
        print(f"Error in download_apk: {e}")
        abort(404)

##############################
# Error Handlers #
##############################

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('error.html', 
                          error_code=404, 
                          error_message="页面不存在"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('error.html', 
                          error_code=500, 
                          error_message="服务器内部错误"), 500

##############################
# Application Entry Point #
##############################

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=32220)
