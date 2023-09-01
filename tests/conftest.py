import pytest

@pytest.fixture()
def document_name(request):
    return request.node.name.replace(" ", "_").replace("/", "_")