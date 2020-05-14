from pathlib import Path
from tempfile import TemporaryDirectory
from nbconvert.exporters import PDFExporter

from ._preprocessors import MarkdownPreprocessor, NoExecuteDataFramePreprocessor, ChangeOutputTypePreprocessor

td = TemporaryDirectory()
td_path = Path(td.name)

class DataFramePDFExporter(PDFExporter):
 
    export_from_notebook = 'PDF - DataFrame as Image'
    # must give specific order of preprocessors
    # custom preprocessors are run after default_preprocessors
    preprocessors = [
        MarkdownPreprocessor(output_dir=td_path, image_dir_name=td_path),
        NoExecuteDataFramePreprocessor,
        ChangeOutputTypePreprocessor,
        'nbconvert.preprocessors.TagRemovePreprocessor',
        'nbconvert.preprocessors.RegexRemovePreprocessor', 
        'nbconvert.preprocessors.coalesce_streams', 
        'nbconvert.preprocessors.SVG2PDFPreprocessor', 
        'nbconvert.preprocessors.LatexPreprocessor', 
        'nbconvert.preprocessors.HighlightMagicsPreprocessor', 
        'nbconvert.preprocessors.ExtractOutputPreprocessor'
        ]
    default_preprocessors = []
