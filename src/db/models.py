from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Text, ForeignKey

Base = declarative_base()

class Repository(Base):
    __tablename__ = 'repositories'
    id = Column(Integer, primary_key=True)
    owner_login = Column(String, nullable=False)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    fetched_at = Column(String, nullable=False)
    pull_requests = relationship('PullRequest', back_populates='repository')

class PullRequest(Base):
    __tablename__ = 'pull_requests'
    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey('repositories.id'), nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    user_login = Column(String, nullable=False)
    state = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    closed_at = Column(String)
    merged_at = Column(String)
    body = Column(Text)
    url = Column(String, nullable=False)
    api_url = Column(String, nullable=False)
    fetched_at = Column(String, nullable=False)
    repository = relationship('Repository', back_populates='pull_requests')
    review_comments = relationship('ReviewComment', back_populates='pull_request')

class ReviewComment(Base):
    __tablename__ = 'review_comments'
    id = Column(Integer, primary_key=True)
    pull_request_id = Column(Integer, ForeignKey('pull_requests.id'), nullable=False)
    user_login = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    api_url = Column(String, nullable=False)
    html_url = Column(String, nullable=False)
    diff_hunk = Column(Text)
    path = Column(String)
    position = Column(Integer)
    original_position = Column(Integer)
    commit_id = Column(String)
    fetched_at = Column(String, nullable=False)
    pull_request = relationship('PullRequest', back_populates='review_comments')

class User(Base):
    __tablename__ = 'users'
    login = Column(String, primary_key=True)
    id = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    name = Column(String)
    email = Column(String)
    fetched_at = Column(String, nullable=False) 