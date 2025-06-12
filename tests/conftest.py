"""
テストの共通設定
"""
from typing import Any

def pytest_configure(config: Any) -> None:
    """pytestの設定"""
    config.addinivalue_line("markers",
        "asyncio: mark test as async"
    ) 