from pathlib import Path
import pytest
from dataframe_image import convert


filenames = ['tests/notebooks/Short Test Notebook EXECUTED.ipynb',
             'tests/notebooks/short notebook with md tables EXECUTED.ipynb']
tos = ['pdf', 'md']

@pytest.mark.parametrize('filename', filenames)
@pytest.mark.parametrize('to', tos)
class TestConvert:    

    def test_same_folder(self, filename, to):
        convert(filename, to=to)

    def test_different_folder(self, filename, to):
        name = Path(filename).name
        convert(filename, to=to, output_dir='tests/test_output', save_notebook=True, 
                document_name=f'{name} NEW NAME')

    def test_execute(self, filename, to):
        name = Path(filename).name
        convert(filename, to=to, document_name=f'{name} EXECUTE', execute=True)
