from dataframe_image import convert
import nbformat

class TestPDF:

    filename = 'notebooks/Test 1 Notebook.ipynb'

    def test_same_folder(self):
        convert(self.filename, to='pdf')

    def test_different_folder(self):
        convert(self.filename, to='pdf', output_dir='notebooks/test_output', save_notebook=True, 
                document_name='Test 1 Notebook NEW NAME')

    def test_no_execute(self):
        convert(self.filename, to='pdf', document_name='Test 1 Notebook NO EXECUTE')


class TestMarkdown:

    filename = 'notebooks/Test 1 Notebook.ipynb'

    def test_same_folder(self):
        convert(self.filename, to='md')

    def test_different_folder(self):
        convert(self.filename, to='md', output_dir='notebooks/test_output', 
                save_notebook=True, document_name='New Test Name')

    def test_no_execute(self):
        convert(self.filename, to='md', document_name='Test 1 Notebook NO EXECUTE')

