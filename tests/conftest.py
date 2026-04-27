from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runintegration",
        action="store_true",
        help="Run integration tests (require TeX install)",
    )
    parser.addoption(
        "--rundiff",
        action="store_true",
        help="Run differential tests (require LATEXMK_PERL env var)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if not config.getoption("--runintegration"):
        skip = pytest.mark.skip(reason="pass --runintegration")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
    if not config.getoption("--rundiff"):
        skip = pytest.mark.skip(reason="pass --rundiff")
        for item in items:
            if "differential" in item.keywords:
                item.add_marker(skip)
