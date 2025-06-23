SAMPLE_PRS = [
    {
        "number": 1,
        "title": "テストPR1",
        "state": "open",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "body": "テストPRの本文1",
        "user": {"login": "testuser1"},
        "html_url": "https://github.com/test/repo/pull/1"
    },
    {
        "number": 2,
        "title": "テストPR2",
        "state": "closed",
        "created_at": "2024-01-03T00:00:00Z",
        "updated_at": "2024-01-04T00:00:00Z",
        "body": "テストPRの本文2",
        "user": {"login": "testuser2"},
        "html_url": "https://github.com/test/repo/pull/2"
    }
]

SAMPLE_COMMENTS = [
    {
        "id": 1,
        "body": "テストコメント1",
        "user": {"login": "reviewer1"},
        "created_at": "2024-01-01T01:00:00Z",
        "html_url": "https://github.com/test/repo/pull/1#issuecomment-1"
    },
    {
        "id": 2,
        "body": "テストコメント2",
        "user": {"login": "reviewer2"},
        "created_at": "2024-01-03T01:00:00Z",
        "html_url": "https://github.com/test/repo/pull/2#issuecomment-2"
    }
] 