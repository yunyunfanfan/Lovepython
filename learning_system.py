#!/usr/bin/env python3
"""
Learning Analysis and Recommendation System
面向对象的学习分析与推荐系统

This module provides a comprehensive object-oriented learning analysis system
with features including:
- Question management with OOP design
- Learning progress tracking
- Statistics analysis
- Intelligent recommendation engine
- Cache management with singleton pattern
- Factory pattern for analyzer creation

Author: yunyunfanfan
License: MIT
"""

import sqlite3
import json
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
import threading
import time


##############################
# Enums and Data Classes
##############################

class QuestionDifficulty(Enum):
    """题目难度枚举"""
    EASY = "易"
    MEDIUM = "中"
    HARD = "难"
    VERY_HARD = "很难"


class QuestionType(Enum):
    """题目类型枚举"""
    SINGLE_CHOICE = "单选题"
    MULTIPLE_CHOICE = "多选题"
    TRUE_FALSE = "判断题"
    FILL_BLANK = "填空题"
    PROGRAMMING = "编程题"


@dataclass
class Question:
    """题目数据类"""
    id: str
    stem: str
    answer: str
    difficulty: Optional[str] = None
    qtype: Optional[str] = None
    category: Optional[str] = None
    options: Dict[str, str] = field(default_factory=dict)
    created_at: Optional[str] = None
    
    def get_difficulty_level(self) -> int:
        """获取难度等级（数值）"""
        difficulty_map = {
            QuestionDifficulty.EASY.value: 1,
            QuestionDifficulty.MEDIUM.value: 2,
            QuestionDifficulty.HARD.value: 3,
            QuestionDifficulty.VERY_HARD.value: 4
        }
        return difficulty_map.get(self.difficulty, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'stem': self.stem,
            'answer': self.answer,
            'difficulty': self.difficulty,
            'type': self.qtype,
            'category': self.category,
            'options': self.options
        }


@dataclass
class UserAnswer:
    """用户答题记录数据类"""
    user_id: int
    question_id: str
    user_answer: str
    correct: bool
    timestamp: datetime
    time_spent: Optional[float] = None  # 答题耗时（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'question_id': self.question_id,
            'user_answer': self.user_answer,
            'correct': self.correct,
            'timestamp': self.timestamp.isoformat(),
            'time_spent': self.time_spent
        }


@dataclass
class LearningProgress:
    """学习进度数据类"""
    user_id: int
    total_questions: int
    answered_questions: int
    correct_count: int
    wrong_count: int
    accuracy_rate: float
    current_seq_qid: Optional[str] = None
    last_active_time: Optional[datetime] = None
    
    def get_completion_rate(self) -> float:
        """获取完成率"""
        if self.total_questions == 0:
            return 0.0
        return (self.answered_questions / self.total_questions) * 100


@dataclass
class Recommendation:
    """推荐结果数据类"""
    question_id: str
    score: float
    reason: str
    priority: int  # 优先级：1-高，2-中，3-低
    
    def __lt__(self, other):
        """用于排序"""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.score > other.score


##############################
# Abstract Base Classes
##############################

class DatabaseAccessor(ABC):
    """数据库访问抽象基类"""
    
    def __init__(self, db_path: str = 'database.db'):
        """
        初始化数据库访问器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    @abstractmethod
    def execute_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """执行查询"""
        pass


class AnalyzerBase(ABC):
    """分析器抽象基类"""
    
    def __init__(self, db_accessor: DatabaseAccessor):
        """
        初始化分析器
        
        Args:
            db_accessor: 数据库访问器
        """
        self.db_accessor = db_accessor
    
    @abstractmethod
    def analyze(self, user_id: int) -> Dict[str, Any]:
        """
        执行分析
        
        Args:
            user_id: 用户ID
            
        Returns:
            分析结果字典
        """
        pass
    
    @abstractmethod
    def get_analysis_name(self) -> str:
        """获取分析器名称"""
        pass


##############################
# Database Accessor Implementation
##############################

class QuestionDatabaseAccessor(DatabaseAccessor):
    """题目数据库访问器"""
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """执行查询"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return results
        finally:
            conn.close()
    
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """执行更新操作"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
    
    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """根据ID获取题目"""
        query = "SELECT * FROM questions WHERE id = ?"
        results = self.execute_query(query, (question_id,))
        if results:
            row = results[0]
            options = json.loads(row['options']) if row['options'] else {}
            return Question(
                id=row['id'],
                stem=row['stem'],
                answer=row['answer'],
                difficulty=row['difficulty'],
                qtype=row['qtype'],
                category=row['category'],
                options=options,
                created_at=dict(row).get('created_at')
            )
        return None
    
    def get_all_questions(self) -> List[Question]:
        """获取所有题目"""
        query = "SELECT * FROM questions"
        results = self.execute_query(query)
        questions = []
        for row in results:
            options = json.loads(row['options']) if row['options'] else {}
            questions.append(Question(
                id=row['id'],
                stem=row['stem'],
                answer=row['answer'],
                difficulty=row['difficulty'],
                qtype=row['qtype'],
                category=row['category'],
                options=options,
                created_at=dict(row).get('created_at')
            ))
        return questions
    
    def get_user_answers(self, user_id: int) -> List[UserAnswer]:
        """获取用户答题记录"""
        query = """
            SELECT question_id, user_answer, correct, timestamp 
            FROM history 
            WHERE user_id = ? 
            ORDER BY timestamp DESC
        """
        results = self.execute_query(query, (user_id,))
        answers = []
        for row in results:
            answers.append(UserAnswer(
                user_id=user_id,
                question_id=row['question_id'],
                user_answer=row['user_answer'],
                correct=bool(row['correct']),
                timestamp=datetime.fromisoformat(row['timestamp'])
            ))
        return answers


##############################
# Question Manager Class
##############################

class QuestionManager:
    """题目管理器类（封装）"""
    
    def __init__(self, db_accessor: QuestionDatabaseAccessor):
        """
        初始化题目管理器
        
        Args:
            db_accessor: 数据库访问器
        """
        self._db_accessor = db_accessor
        self._cache = {}  # 简单的内存缓存
        self._cache_lock = threading.Lock()
    
    def get_question(self, question_id: str) -> Optional[Question]:
        """
        获取题目（带缓存）
        
        Args:
            question_id: 题目ID
            
        Returns:
            题目对象或None
        """
        # 先检查缓存
        with self._cache_lock:
            if question_id in self._cache:
                return self._cache[question_id]
        
        # 从数据库获取
        question = self._db_accessor.get_question_by_id(question_id)
        
        # 存入缓存
        if question:
            with self._cache_lock:
                self._cache[question_id] = question
        
        return question
    
    def get_random_question(self, exclude_ids: List[str] = None) -> Optional[Question]:
        """
        获取随机题目
        
        Args:
            exclude_ids: 要排除的题目ID列表
            
        Returns:
            随机题目对象或None
        """
        all_questions = self._db_accessor.get_all_questions()
        
        if exclude_ids:
            all_questions = [q for q in all_questions if q.id not in exclude_ids]
        
        if not all_questions:
            return None
        
        return random.choice(all_questions)
    
    def get_questions_by_difficulty(self, difficulty: str) -> List[Question]:
        """
        根据难度获取题目
        
        Args:
            difficulty: 难度等级
            
        Returns:
            题目列表
        """
        all_questions = self._db_accessor.get_all_questions()
        return [q for q in all_questions if q.difficulty == difficulty]
    
    def get_questions_by_category(self, category: str) -> List[Question]:
        """
        根据类别获取题目
        
        Args:
            category: 类别名称
            
        Returns:
            题目列表
        """
        all_questions = self._db_accessor.get_all_questions()
        return [q for q in all_questions if q.category == category]
    
    def search_questions(self, keyword: str) -> List[Question]:
        """
        搜索题目
        
        Args:
            keyword: 关键词
            
        Returns:
            匹配的题目列表
        """
        all_questions = self._db_accessor.get_all_questions()
        keyword_lower = keyword.lower()
        return [
            q for q in all_questions 
            if keyword_lower in q.stem.lower() or keyword_lower in q.id.lower()
        ]
    
    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._cache.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取题目统计信息
        
        Returns:
            统计信息字典
        """
        all_questions = self._db_accessor.get_all_questions()
        
        total = len(all_questions)
        difficulty_count = Counter(q.difficulty for q in all_questions if q.difficulty)
        category_count = Counter(q.category for q in all_questions if q.category)
        type_count = Counter(q.qtype for q in all_questions if q.qtype)
        
        return {
            'total': total,
            'difficulty_distribution': dict(difficulty_count),
            'category_distribution': dict(category_count),
            'type_distribution': dict(type_count)
        }


##############################
# Learning Progress Tracker Class
##############################

class LearningProgressTracker(AnalyzerBase):
    """学习进度追踪器类（继承自AnalyzerBase）"""
    
    def __init__(self, db_accessor: DatabaseAccessor, question_manager: QuestionManager):
        """
        初始化学习进度追踪器
        
        Args:
            db_accessor: 数据库访问器
            question_manager: 题目管理器
        """
        super().__init__(db_accessor)
        self.question_manager = question_manager
    
    def analyze(self, user_id: int) -> Dict[str, Any]:
        """
        分析用户学习进度
        
        Args:
            user_id: 用户ID
            
        Returns:
            学习进度分析结果
        """
        db_accessor = QuestionDatabaseAccessor()
        user_answers = db_accessor.get_user_answers(user_id)
        all_questions = self.question_manager._db_accessor.get_all_questions()
        
        total_questions = len(all_questions)
        answered_question_ids = set(answer.question_id for answer in user_answers)
        answered_count = len(answered_question_ids)
        
        correct_count = sum(1 for answer in user_answers if answer.correct)
        wrong_count = len(user_answers) - correct_count
        
        accuracy_rate = (correct_count / len(user_answers) * 100) if user_answers else 0.0
        
        # 获取当前顺序答题位置
        conn = self.db_accessor.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT current_seq_qid FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            current_seq_qid = row['current_seq_qid'] if row else None
        finally:
            conn.close()
        
        progress = LearningProgress(
            user_id=user_id,
            total_questions=total_questions,
            answered_questions=answered_count,
            correct_count=correct_count,
            wrong_count=wrong_count,
            accuracy_rate=accuracy_rate,
            current_seq_qid=current_seq_qid,
            last_active_time=datetime.now()
        )
        
        return {
            'progress': progress,
            'completion_rate': progress.get_completion_rate(),
            'statistics': {
                'total': total_questions,
                'answered': answered_count,
                'remaining': total_questions - answered_count,
                'correct': correct_count,
                'wrong': wrong_count,
                'accuracy': accuracy_rate
            }
        }
    
    def get_analysis_name(self) -> str:
        """获取分析器名称"""
        return "学习进度追踪"
    
    def get_wrong_questions(self, user_id: int) -> List[Question]:
        """
        获取错题列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            错题列表
        """
        db_accessor = QuestionDatabaseAccessor()
        user_answers = db_accessor.get_user_answers(user_id)
        
        wrong_question_ids = {
            answer.question_id 
            for answer in user_answers 
            if not answer.correct
        }
        
        wrong_questions = []
        for qid in wrong_question_ids:
            question = self.question_manager.get_question(qid)
            if question:
                wrong_questions.append(question)
        
        return wrong_questions
    
    def get_learning_trend(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """
        获取学习趋势
        
        Args:
            user_id: 用户ID
            days: 天数
            
        Returns:
            学习趋势数据
        """
        db_accessor = QuestionDatabaseAccessor()
        user_answers = db_accessor.get_user_answers(user_id)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_stats = defaultdict(lambda: {'total': 0, 'correct': 0})
        
        for answer in user_answers:
            if start_date <= answer.timestamp <= end_date:
                date_key = answer.timestamp.date().isoformat()
                daily_stats[date_key]['total'] += 1
                if answer.correct:
                    daily_stats[date_key]['correct'] += 1
        
        trend_data = []
        for date_key in sorted(daily_stats.keys()):
            stats = daily_stats[date_key]
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            trend_data.append({
                'date': date_key,
                'total': stats['total'],
                'correct': stats['correct'],
                'accuracy': accuracy
            })
        
        return {
            'period': f'{days}天',
            'data': trend_data
        }


##############################
# Statistics Analyzer Class
##############################

class StatisticsAnalyzer(AnalyzerBase):
    """统计分析器类（继承自AnalyzerBase）"""
    
    def __init__(self, db_accessor: DatabaseAccessor, question_manager: QuestionManager):
        """
        初始化统计分析器
        
        Args:
            db_accessor: 数据库访问器
            question_manager: 题目管理器
        """
        super().__init__(db_accessor)
        self.question_manager = question_manager
    
    def analyze(self, user_id: int) -> Dict[str, Any]:
        """
        执行统计分析
        
        Args:
            user_id: 用户ID
            
        Returns:
            统计分析结果
        """
        db_accessor = QuestionDatabaseAccessor()
        user_answers = db_accessor.get_user_answers(user_id)
        
        if not user_answers:
            return {
                'overall_accuracy': 0.0,
                'difficulty_stats': {},
                'category_stats': {},
                'type_stats': {},
                'weak_areas': []
            }
        
        # 总体正确率
        correct_count = sum(1 for answer in user_answers if answer.correct)
        overall_accuracy = (correct_count / len(user_answers)) * 100
        
        # 按难度统计
        difficulty_stats = defaultdict(lambda: {'total': 0, 'correct': 0})
        category_stats = defaultdict(lambda: {'total': 0, 'correct': 0})
        type_stats = defaultdict(lambda: {'total': 0, 'correct': 0})
        
        for answer in user_answers:
            question = self.question_manager.get_question(answer.question_id)
            if question:
                if question.difficulty:
                    difficulty_stats[question.difficulty]['total'] += 1
                    if answer.correct:
                        difficulty_stats[question.difficulty]['correct'] += 1
                
                if question.category:
                    category_stats[question.category]['total'] += 1
                    if answer.correct:
                        category_stats[question.category]['correct'] += 1
                
                if question.qtype:
                    type_stats[question.qtype]['total'] += 1
                    if answer.correct:
                        type_stats[question.qtype]['correct'] += 1
        
        # 计算准确率
        def calc_accuracy(stats_dict):
            result = {}
            for key, value in stats_dict.items():
                accuracy = (value['correct'] / value['total'] * 100) if value['total'] > 0 else 0
                result[key] = {
                    'total': value['total'],
                    'correct': value['correct'],
                    'accuracy': accuracy
                }
            return result
        
        difficulty_accuracy = calc_accuracy(difficulty_stats)
        category_accuracy = calc_accuracy(category_stats)
        type_accuracy = calc_accuracy(type_stats)
        
        # 找出薄弱环节（准确率低于60%的类别）
        weak_areas = [
            {'category': cat, 'accuracy': stats['accuracy']}
            for cat, stats in category_accuracy.items()
            if stats['accuracy'] < 60 and stats['total'] >= 3
        ]
        weak_areas.sort(key=lambda x: x['accuracy'])
        
        return {
            'overall_accuracy': overall_accuracy,
            'difficulty_stats': difficulty_accuracy,
            'category_stats': category_accuracy,
            'type_stats': type_accuracy,
            'weak_areas': weak_areas[:5]  # 返回前5个薄弱环节
        }
    
    def get_analysis_name(self) -> str:
        """获取分析器名称"""
        return "统计分析"
    
    def get_difficulty_analysis(self, user_id: int) -> Dict[str, Any]:
        """
        获取难度分析
        
        Args:
            user_id: 用户ID
            
        Returns:
            难度分析结果
        """
        analysis = self.analyze(user_id)
        return {
            'difficulty_stats': analysis['difficulty_stats'],
            'recommendations': self._generate_difficulty_recommendations(analysis['difficulty_stats'])
        }
    
    def _generate_difficulty_recommendations(self, difficulty_stats: Dict[str, Any]) -> List[str]:
        """生成难度相关建议"""
        recommendations = []
        
        for difficulty, stats in difficulty_stats.items():
            if stats['accuracy'] < 50:
                recommendations.append(
                    f"在{difficulty}难度的题目上表现较弱，建议加强练习"
                )
            elif stats['accuracy'] > 90:
                recommendations.append(
                    f"在{difficulty}难度的题目上表现优秀，可以尝试更高难度的题目"
                )
        
        return recommendations


##############################
# Recommendation Engine Class
##############################

class RecommendationEngine:
    """推荐引擎类"""
    
    def __init__(self, db_accessor: DatabaseAccessor, question_manager: QuestionManager):
        """
        初始化推荐引擎
        
        Args:
            db_accessor: 数据库访问器
            question_manager: 题目管理器
        """
        self.db_accessor = db_accessor
        self.question_manager = question_manager
        self.statistics_analyzer = StatisticsAnalyzer(db_accessor, question_manager)
        self.progress_tracker = LearningProgressTracker(db_accessor, question_manager)
    
    def recommend_questions(self, user_id: int, count: int = 10) -> List[Recommendation]:
        """
        推荐题目
        
        Args:
            user_id: 用户ID
            count: 推荐数量
            
        Returns:
            推荐题目列表
        """
        # 获取用户答题记录
        db_accessor = QuestionDatabaseAccessor()
        user_answers = db_accessor.get_user_answers(user_id)
        answered_question_ids = {answer.question_id for answer in user_answers}
        
        # 获取所有题目
        all_questions = self.question_manager._db_accessor.get_all_questions()
        unanswered_questions = [q for q in all_questions if q.id not in answered_question_ids]
        
        # 获取统计分析
        stats = self.statistics_analyzer.analyze(user_id)
        
        # 计算推荐分数
        recommendations = []
        for question in unanswered_questions:
            score = self._calculate_recommendation_score(question, user_answers, stats)
            reason = self._generate_recommendation_reason(question, stats)
            priority = self._determine_priority(score)
            
            recommendations.append(Recommendation(
                question_id=question.id,
                score=score,
                reason=reason,
                priority=priority
            ))
        
        # 按优先级和分数排序
        recommendations.sort()
        
        return recommendations[:count]
    
    def _calculate_recommendation_score(self, question: Question, 
                                        user_answers: List[UserAnswer],
                                        stats: Dict[str, Any]) -> float:
        """
        计算推荐分数
        
        Args:
            question: 题目对象
            user_answers: 用户答题记录
            stats: 统计分析结果
            
        Returns:
            推荐分数（0-100）
        """
        score = 50.0  # 基础分数
        
        # 根据薄弱环节加分
        weak_areas = stats.get('weak_areas', [])
        if question.category in [area['category'] for area in weak_areas]:
            score += 30
        
        # 根据难度加分（如果用户在该难度表现不佳）
        difficulty_stats = stats.get('difficulty_stats', {})
        if question.difficulty in difficulty_stats:
            difficulty_accuracy = difficulty_stats[question.difficulty]['accuracy']
            if difficulty_accuracy < 60:
                score += 20
        
        # 根据题目类型加分
        type_stats = stats.get('type_stats', {})
        if question.qtype in type_stats:
            type_accuracy = type_stats[question.qtype]['accuracy']
            if type_accuracy < 70:
                score += 15
        
        # 随机因子（避免总是推荐相同的题目）
        score += random.uniform(-5, 5)
        
        return min(100.0, max(0.0, score))
    
    def _generate_recommendation_reason(self, question: Question, 
                                      stats: Dict[str, Any]) -> str:
        """生成推荐理由"""
        reasons = []
        
        weak_areas = stats.get('weak_areas', [])
        if question.category in [area['category'] for area in weak_areas]:
            reasons.append(f"属于薄弱环节：{question.category}")
        
        difficulty_stats = stats.get('difficulty_stats', {})
        if question.difficulty in difficulty_stats:
            difficulty_accuracy = difficulty_stats[question.difficulty]['accuracy']
            if difficulty_accuracy < 60:
                reasons.append(f"该难度题目需要加强练习")
        
        if not reasons:
            reasons.append("根据您的学习情况推荐")
        
        return "；".join(reasons)
    
    def _determine_priority(self, score: float) -> int:
        """确定优先级"""
        if score >= 70:
            return 1  # 高优先级
        elif score >= 50:
            return 2  # 中优先级
        else:
            return 3  # 低优先级
    
    def recommend_wrong_questions(self, user_id: int, count: int = 5) -> List[Recommendation]:
        """
        推荐错题复习
        
        Args:
            user_id: 用户ID
            count: 推荐数量
            
        Returns:
            推荐错题列表
        """
        progress_tracker = LearningProgressTracker(self.db_accessor, self.question_manager)
        wrong_questions = progress_tracker.get_wrong_questions(user_id)
        
        # 获取错题答题记录
        db_accessor = QuestionDatabaseAccessor()
        user_answers = db_accessor.get_user_answers(user_id)
        
        wrong_answers = {
            answer.question_id: answer 
            for answer in user_answers 
            if not answer.correct
        }
        
        recommendations = []
        for question in wrong_questions[:count]:
            answer = wrong_answers.get(question.id)
            if answer:
                # 根据错误次数和最近错误时间计算优先级
                error_count = sum(
                    1 for a in user_answers 
                    if a.question_id == question.id and not a.correct
                )
                days_since_error = (datetime.now() - answer.timestamp).days
                
                score = min(100, error_count * 20 + days_since_error * 2)
                priority = 1 if error_count >= 2 else 2
                
                recommendations.append(Recommendation(
                    question_id=question.id,
                    score=score,
                    reason=f"已错误{error_count}次，建议重点复习",
                    priority=priority
                ))
        
        recommendations.sort()
        return recommendations


##############################
# Cache Manager (Singleton Pattern)
##############################

class CacheManager:
    """缓存管理器（单例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CacheManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化缓存管理器"""
        if self._initialized:
            return
        
        self._cache = {}
        self._cache_timestamps = {}
        self._max_size = 1000
        self._ttl = 3600  # 缓存过期时间（秒）
        self._lock = threading.Lock()
        self._initialized = True
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或None
        """
        with self._lock:
            if key in self._cache:
                # 检查是否过期
                if key in self._cache_timestamps:
                    if time.time() - self._cache_timestamps[key] < self._ttl:
                        return self._cache[key]
                    else:
                        # 过期，删除
                        del self._cache[key]
                        del self._cache_timestamps[key]
                else:
                    return self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            # 如果缓存已满，删除最旧的项
            if len(self._cache) >= self._max_size:
                self._evict_oldest()
            
            self._cache[key] = value
            self._cache_timestamps[key] = time.time()
    
    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]
    
    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._cache_timestamps.clear()
    
    def _evict_oldest(self):
        """删除最旧的缓存项"""
        if not self._cache_timestamps:
            return
        
        oldest_key = min(self._cache_timestamps.keys(), 
                        key=lambda k: self._cache_timestamps[k])
        self.delete(oldest_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'ttl': self._ttl
            }


##############################
# Factory Pattern
##############################

class AnalyzerFactory:
    """分析器工厂类（工厂模式）"""
    
    @staticmethod
    def create_analyzer(analyzer_type: str, db_accessor: DatabaseAccessor, 
                        question_manager: QuestionManager) -> AnalyzerBase:
        """
        创建分析器
        
        Args:
            analyzer_type: 分析器类型（'progress', 'statistics', 'recommendation'）
            db_accessor: 数据库访问器
            question_manager: 题目管理器
            
        Returns:
            分析器实例
        """
        if analyzer_type == 'progress':
            return LearningProgressTracker(db_accessor, question_manager)
        elif analyzer_type == 'statistics':
            return StatisticsAnalyzer(db_accessor, question_manager)
        else:
            raise ValueError(f"Unknown analyzer type: {analyzer_type}")
    
    @staticmethod
    def create_recommendation_engine(db_accessor: DatabaseAccessor,
                                     question_manager: QuestionManager) -> RecommendationEngine:
        """
        创建推荐引擎
        
        Args:
            db_accessor: 数据库访问器
            question_manager: 题目管理器
            
        Returns:
            推荐引擎实例
        """
        return RecommendationEngine(db_accessor, question_manager)


##############################
# Main Learning System Class
##############################

class LearningSystem:
    """学习系统主类（组合模式）"""
    
    def __init__(self, db_path: str = 'database.db'):
        """
        初始化学习系统
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_accessor = QuestionDatabaseAccessor(db_path)
        self.question_manager = QuestionManager(self.db_accessor)
        self.cache_manager = CacheManager()
        self.progress_tracker = LearningProgressTracker(self.db_accessor, self.question_manager)
        self.statistics_analyzer = StatisticsAnalyzer(self.db_accessor, self.question_manager)
        self.recommendation_engine = RecommendationEngine(self.db_accessor, self.question_manager)
    
    def get_user_progress(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户学习进度
        
        Args:
            user_id: 用户ID
            
        Returns:
            学习进度信息
        """
        cache_key = f"progress_{user_id}"
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        result = self.progress_tracker.analyze(user_id)
        self.cache_manager.set(cache_key, result)
        
        return result
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户统计数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            统计数据
        """
        cache_key = f"statistics_{user_id}"
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        result = self.statistics_analyzer.analyze(user_id)
        self.cache_manager.set(cache_key, result)
        
        return result
    
    def get_recommendations(self, user_id: int, count: int = 10) -> List[Dict[str, Any]]:
        """
        获取题目推荐
        
        Args:
            user_id: 用户ID
            count: 推荐数量
            
        Returns:
            推荐列表
        """
        recommendations = self.recommendation_engine.recommend_questions(user_id, count)
        return [rec.__dict__ for rec in recommendations]
    
    def get_wrong_question_recommendations(self, user_id: int, count: int = 5) -> List[Dict[str, Any]]:
        """
        获取错题推荐
        
        Args:
            user_id: 用户ID
            count: 推荐数量
            
        Returns:
            错题推荐列表
        """
        recommendations = self.recommendation_engine.recommend_wrong_questions(user_id, count)
        return [rec.__dict__ for rec in recommendations]
    
    def clear_user_cache(self, user_id: int):
        """清空用户相关缓存"""
        self.cache_manager.delete(f"progress_{user_id}")
        self.cache_manager.delete(f"statistics_{user_id}")


# 导出主要类和函数
__all__ = [
    'Question',
    'UserAnswer',
    'LearningProgress',
    'Recommendation',
    'QuestionDifficulty',
    'QuestionType',
    'DatabaseAccessor',
    'AnalyzerBase',
    'QuestionDatabaseAccessor',
    'QuestionManager',
    'LearningProgressTracker',
    'StatisticsAnalyzer',
    'RecommendationEngine',
    'CacheManager',
    'AnalyzerFactory',
    'LearningSystem'
]

