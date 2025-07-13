from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Repository(Base):
    __tablename__ = 'repositories'
    id = Column(Integer, primary_key=True)
    owner_login = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    fetched_at = Column(Text, nullable=False)
    pull_requests = relationship('PullRequest', back_populates='repository')

class PullRequest(Base):
    __tablename__ = 'pull_requests'
    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey('repositories.id'), nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    user_login = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    closed_at = Column(Text)
    merged_at = Column(Text)
    body = Column(Text)
    url = Column(Text, nullable=False)
    api_url = Column(Text, nullable=False)
    fetched_at = Column(Text, nullable=False)
    repository = relationship('Repository', back_populates='pull_requests')
    review_comments = relationship('ReviewComment', back_populates='pull_request')

class ReviewComment(Base):
    __tablename__ = 'review_comments'
    id = Column(Integer, primary_key=True)
    pull_request_id = Column(Integer, ForeignKey('pull_requests.id'), nullable=False)
    user_login = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    api_url = Column(Text, nullable=False)
    html_url = Column(Text, nullable=False)
    diff_hunk = Column(Text)
    path = Column(Text)
    position = Column(Integer)
    original_position = Column(Integer)
    commit_id = Column(Text)
    fetched_at = Column(Text, nullable=False)
    pull_request = relationship('PullRequest', back_populates='review_comments')

class User(Base):
    __tablename__ = 'users'
    login = Column(Text, primary_key=True)
    id = Column(Integer, nullable=False)
    type = Column(Text, nullable=False)
    name = Column(Text)
    email = Column(Text)
    fetched_at = Column(Text, nullable=False)