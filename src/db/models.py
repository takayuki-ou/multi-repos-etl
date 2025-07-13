from sqlalchemy.orm import declarative_base, relationship, validates
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index, CheckConstraint
from sqlalchemy.dialects.sqlite import DATETIME
from datetime import datetime
from typing import Optional

Base = declarative_base()

class Repository(Base):
    __tablename__ = 'repositories'
    
    id = Column(Integer, primary_key=True)
    owner_login = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    created_at = Column(String(50), nullable=False)  # ISO 8601 format
    updated_at = Column(String(50), nullable=False)  # ISO 8601 format
    fetched_at = Column(String(50), nullable=False)  # ISO 8601 format
    
    # リレーションシップ
    pull_requests = relationship('PullRequest', back_populates='repository', cascade='all, delete-orphan')
    
    # 複合インデックス
    __table_args__ = (
        Index('idx_repositories_owner_name', 'owner_login', 'name', unique=True),
        Index('idx_repositories_fetched_at', 'fetched_at'),
    )
    
    @validates('owner_login', 'name')
    def validate_not_empty(self, key, value):
        if not value or not value.strip():
            raise ValueError(f'{key} cannot be empty')
        return value.strip()
    
    @validates('url')
    def validate_url(self, key, value):
        if not value or not value.startswith('http'):
            raise ValueError('URL must be a valid HTTP URL')
        return value

class PullRequest(Base):
    __tablename__ = 'pull_requests'
    
    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False, index=True)
    number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    user_login = Column(String(100), nullable=False, index=True)
    state = Column(String(20), nullable=False)
    created_at = Column(String(50), nullable=False)  # ISO 8601 format
    updated_at = Column(String(50), nullable=False)  # ISO 8601 format
    closed_at = Column(String(50))  # ISO 8601 format
    merged_at = Column(String(50))  # ISO 8601 format
    body = Column(Text)
    url = Column(String(500), nullable=False)
    api_url = Column(String(500), nullable=False)
    fetched_at = Column(String(50), nullable=False)  # ISO 8601 format
    
    # リレーションシップ
    repository = relationship('Repository', back_populates='pull_requests')
    review_comments = relationship('ReviewComment', back_populates='pull_request', cascade='all, delete-orphan')
    
    # インデックスと制約
    __table_args__ = (
        Index('idx_pull_requests_repo_number', 'repository_id', 'number', unique=True),
        Index('idx_pull_requests_state', 'state'),
        Index('idx_pull_requests_created_at', 'created_at'),
        Index('idx_pull_requests_updated_at', 'updated_at'),
        Index('idx_pull_requests_user', 'user_login'),
        CheckConstraint("state IN ('open', 'closed', 'merged')", name='valid_pr_state'),
    )
    
    @validates('state')
    def validate_state(self, key, value):
        valid_states = ['open', 'closed', 'merged']
        if value not in valid_states:
            raise ValueError(f'State must be one of: {valid_states}')
        return value
    
    @validates('number')
    def validate_number(self, key, value):
        if value <= 0:
            raise ValueError('PR number must be positive')
        return value

class ReviewComment(Base):
    __tablename__ = 'review_comments'
    
    id = Column(Integer, primary_key=True)
    pull_request_id = Column(Integer, ForeignKey('pull_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    user_login = Column(String(100), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(String(50), nullable=False)  # ISO 8601 format
    updated_at = Column(String(50), nullable=False)  # ISO 8601 format
    api_url = Column(String(500), nullable=False)
    html_url = Column(String(500), nullable=False, unique=True)
    diff_hunk = Column(Text)
    path = Column(String(500))
    position = Column(Integer)
    original_position = Column(Integer)
    commit_id = Column(String(100))
    fetched_at = Column(String(50), nullable=False)  # ISO 8601 format
    
    # リレーションシップ
    pull_request = relationship('PullRequest', back_populates='review_comments')
    
    # インデックス
    __table_args__ = (
        Index('idx_review_comments_pr_id', 'pull_request_id'),
        Index('idx_review_comments_created_at', 'created_at'),
        Index('idx_review_comments_updated_at', 'updated_at'),
        Index('idx_review_comments_user', 'user_login'),
        Index('idx_review_comments_path', 'path'),
    )
    
    @validates('body')
    def validate_body(self, key, value):
        if not value or not value.strip():
            raise ValueError('Comment body cannot be empty')
        return value.strip()
    
    @validates('html_url')
    def validate_html_url(self, key, value):
        if not value or not value.startswith('http'):
            raise ValueError('HTML URL must be a valid HTTP URL')
        return value

class User(Base):
    __tablename__ = 'users'
    
    login = Column(String(100), primary_key=True)
    id = Column(Integer, nullable=False, unique=True)
    type = Column(String(50), nullable=False)
    name = Column(String(200))
    email = Column(String(200))
    fetched_at = Column(String(50), nullable=False)  # ISO 8601 format
    
    # インデックス
    __table_args__ = (
        Index('idx_users_type', 'type'),
        Index('idx_users_fetched_at', 'fetched_at'),
    )
    
    @validates('type')
    def validate_type(self, key, value):
        valid_types = ['User', 'Organization', 'Bot']
        if value not in valid_types:
            raise ValueError(f'User type must be one of: {valid_types}')
        return value
    
    @validates('email')
    def validate_email(self, key, value):
        if value and '@' not in value:
            raise ValueError('Email must contain @ symbol')
        return value

# データベースの整合性を保つためのヘルパー関数
def validate_iso8601_datetime(date_string: str) -> bool:
    """ISO 8601形式の日時文字列を検証"""
    try:
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False

def sanitize_string(value: str, max_length: int = 500) -> str:
    """文字列をサニタイズして最大長を制限"""
    if not value:
        return ""
    sanitized = value.strip()
    return sanitized[:max_length] if len(sanitized) > max_length else sanitized 