import shutil

from nbconvert.exporters import PDFExporter

from ._preprocessors import (
    ChangeOutputTypePreprocessor,
    MarkdownPreprocessor,
    NoExecuteDataFramePreprocessor,
)


def get_latex_command():
    texs = ["xelatex", "pdflatex", "texi2pdf"]
    final_tex = ""
    for tex in texs:
        if shutil.which(tex):
            final_tex = tex
            break

    if not final_tex:
        raise OSError(
            "No latex installation found. "
            "Try downloading as pdf via browser instead.\n"
            "Find out how to install latex here: "
            "https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex"
        )
    latex_command = [final_tex, "{filename}"]
    if final_tex == "xelatex":
        latex_command.append("-quiet")
    return latex_command


class DataFramePDFExporter(PDFExporter):
    export_from_notebook = "PDF - DataFrame as Image (via latex)"
    latex_command = get_latex_command()
    # must give specific order of preprocessors
    # custom preprocessors are run after default_preprocessors
    preprocessors = [
        MarkdownPreprocessor(),
        NoExecuteDataFramePreprocessor,
        ChangeOutputTypePreprocessor,
        "nbconvert.preprocessors.TagRemovePreprocessor",
        "nbconvert.preprocessors.RegexRemovePreprocessor",
        "nbconvert.preprocessors.coalesce_streams",
        "nbconvert.preprocessors.SVG2PDFPreprocessor",
        "nbconvert.preprocessors.LatexPreprocessor",
        "nbconvert.preprocessors.HighlightMagicsPreprocessor",
        "nbconvert.preprocessors.ExtractOutputPreprocessor",
    ]
    default_preprocessors = []
