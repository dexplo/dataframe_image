from dataframe_image import convert
import nbformat

class TestPDF:

    filename = 'notebooks/Test_1 Notebook.ipynb'

    def test_same_folder(self):
        convert(self.filename, to='pdf')

    def test_different_folder(self):
        convert(self.filename, to='pdf', output_dir='test_output', save_notebook=True, 
                document_name='New Test Name')