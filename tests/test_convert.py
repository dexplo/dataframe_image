from pathlib import Path

import pytest

from dataframe_image import convert

filenames = [
    "tests/notebooks/Short.ipynb",
    "tests/notebooks/Test 1.ipynb",
    "tests/notebooks/Test 1 EXECUTED.ipynb",
]
uses = [
    "latex",
    "browser",
]
executes = [True, False]

no_input = [True, False]


@pytest.mark.parametrize("filename", filenames)
@pytest.mark.parametrize("use", uses)
@pytest.mark.parametrize("execute", executes, ids=["executed", ""])
@pytest.mark.parametrize("no_input", no_input, ids=["no_input", ""])
class TestConvertPDF:
    def test_to_pdf(self, document_name, filename, use, execute, no_input):
        convert(
            filename,
            to="pdf",
            use=use,
            execute=execute,
            document_name=document_name,
            no_input=no_input,
            output_dir="tests/test_output",
        )


@pytest.mark.parametrize("filename", filenames)
@pytest.mark.parametrize("execute", executes, ids=["executed", ""])
@pytest.mark.parametrize("no_input", no_input, ids=["no_input", ""])
class TestConvertMD:
    def test_to_md(self, document_name, filename, execute, no_input):
        convert(
            filename,
            to="md",
            execute=execute,
            document_name=document_name,
            no_input=no_input,
            output_dir="tests/test_output",
        )


class TestConvertOther:
    def test_save_notebook(self):
        filename = "tests/notebooks/Short.ipynb"
        to = "pdf"
        document_name = Path(filename).stem + " saved NEW NAME"
        convert(
            filename,
            to=to,
            save_notebook=True,
            execute=True,
            document_name=document_name,
            output_dir="tests/test_output",
        )

    def test_matplotlib(self):
        filename = "tests/notebooks/Test 1.ipynb"
        to = "pdf"
        document_name = Path(filename).stem + " matplotlib NEW NAME"
        convert(
            filename,
            to=to,
            execute=True,
            document_name=document_name,
            table_conversion="matplotlib",
            output_dir="tests/test_output",
        )
