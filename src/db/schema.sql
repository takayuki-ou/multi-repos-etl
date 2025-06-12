-- repositoriesテーブル
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY,
    owner_login TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);

-- pull_requestsテーブル
CREATE TABLE IF NOT EXISTS pull_requests (
    id INTEGER PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id),
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    user_login TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT,
    merged_at TEXT,
    body TEXT, -- PR本文を追加
    url TEXT NOT NULL,
    api_url TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);

-- review_commentsテーブル
CREATE TABLE IF NOT EXISTS review_comments (
    id INTEGER PRIMARY KEY,
    pull_request_id INTEGER NOT NULL REFERENCES pull_requests(id),
    user_login TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    api_url TEXT NOT NULL,
    html_url TEXT NOT NULL,
    diff_hunk TEXT,
    path TEXT,
    position INTEGER,
    original_position INTEGER,
    commit_id TEXT,
    fetched_at TEXT NOT NULL
);

-- usersテーブル
CREATE TABLE IF NOT EXISTS users (
    login TEXT PRIMARY KEY,
    id INTEGER NOT NULL,
    type TEXT NOT NULL,
    name TEXT,
    email TEXT,
    fetched_at TEXT NOT NULL
);

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_pull_requests_repository_id ON pull_requests(repository_id);
CREATE INDEX IF NOT EXISTS idx_pull_requests_created_at ON pull_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_pull_requests_updated_at ON pull_requests(updated_at);
CREATE INDEX IF NOT EXISTS idx_review_comments_pull_request_id ON review_comments(pull_request_id);
CREATE INDEX IF NOT EXISTS idx_review_comments_created_at ON review_comments(created_at);
CREATE INDEX IF NOT EXISTS idx_review_comments_updated_at ON review_comments(updated_at);