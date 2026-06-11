"""Pytest configuration for the GROUP_8 test suite."""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that require a live DB2 connection.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--integration"):
        skip = pytest.mark.skip(reason="Pass --integration to run live-DB2 tests.")
        for item in items:
            if item.get_closest_marker("integration"):
                item.add_marker(skip)
