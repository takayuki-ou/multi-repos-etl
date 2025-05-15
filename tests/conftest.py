"""
テストの共通設定
"""
import pytest

def pytest_configure(config):
    """pytestの設定"""
    config.addinivalue_line("markers",
        "asyncio: mark test as async"
    ) 