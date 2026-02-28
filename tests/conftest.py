import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_playwright():
    from dataframe_image.converter.browser import playwright_converter
    playwright_converter.MATHJAX_TIMEOUT = 50000
    playwright_converter.SCREENSHOT_TIMEOUT = 100000

@pytest.fixture(scope="session", autouse=True)
def ensure_output_dir():
    from pathlib import Path

    output_dir = Path("tests/test_output")
    output_dir.mkdir(exist_ok=True, parents=True)


@pytest.fixture()
def document_name(request):
    return request.node.name.replace(" ", "_").replace("/", "_")
