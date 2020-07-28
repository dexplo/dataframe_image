import base64
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import re
import io
import shutil
import urllib.parse

import nbformat
from nbconvert import MarkdownExporter, PDFExporter
from nbconvert.preprocessors import ExecutePreprocessor

from ._preprocessors import (MarkdownPreprocessor, 
                             NoExecuteDataFramePreprocessor, 
                             ChangeOutputTypePreprocessor)

from matplotlib import image as mimage


class Converter:
    KINDS = ['pdf', 'md']
    DISPLAY_DATA_PRIORITY = [
        "image/png",
        "text/html",
        "application/pdf",
        "text/latex",
        "image/svg+xml",
        "image/jpeg",
        "text/markdown",
        "text/plain",
    ]

    def __init__(self, filename, to, use, center_df, max_rows, max_cols, execute, 
                 save_notebook, limit, document_name, table_conversion, chrome_path, 
                 latex_command, output_dir, web_app):
        self.filename = Path(filename)
        self.use = use
        self.center_df = center_df
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.chrome_path = chrome_path
        self.limit = limit
        self.table_conversion = table_conversion
        self.web_app = web_app
        self.td = TemporaryDirectory()

        self.nb_home = self.filename.parent
        self.nb_name = self.filename.stem
        self.to = self.get_to(to)
        self.latex_command = self.get_latex_command(latex_command)
        self.nb = self.get_notebook()

        self.document_name = self.get_document_name(document_name)
        self.execute = execute
        self.save_notebook = save_notebook
        self.final_nb_home = self.get_new_notebook_home(output_dir)
        self.image_dir_name = self.nb_name + '_files'
        
        self.return_data = {}
        self.resources = self.get_resources()

    def get_to(self, to):
        if isinstance(to, str):
            to = [to]
        elif not isinstance(to, list):
            raise TypeError('`to` must either be a string or a list. '
                            'Possible values are "pdf" and "markdown/md"')
        to = set(to)
        if 'markdown' in to:
            to.remove('markdown')
            to.add('md')
        for kind in to:
            if kind not in self.KINDS:
                raise TypeError(
                    "`to` must either be a string or a list. "
                    'Possible values are "pdf" or "markdown"/"md" '
                    f'and not {kind}.'
                )
        if 'pdf' in to:
            to.remove('pdf')
            if self.use == 'latex':
                to.add('pdf_latex')
            elif self.use == 'browser':
                to.add('pdf_browser')
            else:
                raise ValueError('`use` must be either "latex" or "browser"')
        return to

    def get_latex_command(self, latex_command):
        if 'pdf_latex' in self.to:
            if latex_command is None:
                texs = ['xelatex', 'pdflatex', 'texi2pdf']
                final_tex = ''
                for tex in texs:
                    if shutil.which(tex):
                        final_tex = tex
                        break
                if not final_tex:
                    raise OSError('No latex installation found. Try setting `use="browser" to '\
                                  'convert via browser (without latex).\n'\
                                  'Find out how to install latex here: '\
                                  'https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex')
                latex_command = [final_tex, '{filename}']
                if final_tex == 'xelatex':
                    latex_command.append('-quiet')
            return latex_command

    def get_notebook(self):
        with open(self.filename) as f:
            nb = nbformat.read(f, as_version=4)

        if isinstance(self.limit, int):
            nb["cells"] = nb["cells"][:self.limit]

        return nb

    def get_document_name(self, document_name):
        if document_name:
            return document_name
        else:
            return self.nb_name

    def get_new_notebook_home(self, output_dir):
        if output_dir:
            p = Path(output_dir)
            if not p.exists():
                raise FileNotFoundError(f'Directory {p} does not exist')
            elif not p.is_dir():
                raise FileNotFoundError(f'{p} is not a directory')
            return p
        else:
            return Path(self.nb_home)

    def get_resources(self):
        if self.table_conversion == 'chrome':
            from ._screenshot import Screenshot
            converter = Screenshot(center_df=self.center_df, max_rows=self.max_rows, 
                                    max_cols=self.max_cols, chrome_path=self.chrome_path).run
        else:
            from ._matplotlib_table import TableMaker
            converter = TableMaker(fontsize=22).run

        resources = {'metadata': {'path': str(self.nb_home), 
                                  'name': self.document_name},
                     'converter': converter,
                     'image_data_dict': {}}
        return resources
        
    def get_code_to_run(self):
        code = (
            "import pandas as pd;"
            "from dataframe_image._screenshot import make_repr_png;"
            f"_repr_png_ = make_repr_png(center_df={self.center_df}, "
            f"max_rows={self.max_rows}, max_cols={self.max_cols}, "
            f"chrome_path={self.chrome_path});"
            "pd.DataFrame._repr_png_ = _repr_png_;"
            "from pandas.io.formats.style import Styler;"
            "Styler._repr_png_ = _repr_png_;"
            "del make_repr_png, _repr_png_"
        )
        return code

    def execute_notebook(self):
        if self.execute:
            if self.table_conversion == 'chrome':
                code = self.get_code_to_run()
                extra_arguments = [f"--InteractiveShellApp.code_to_run='{code}'"]
            else:
                extra_arguments = []
            pp = ExecutePreprocessor(allow_errors=True, extra_arguments=extra_arguments)
            pp.preprocess(self.nb, self.resources)

    def no_execute_preprocess(self):
        if not self.execute or self.table_conversion == 'matplotlib':
            NoExecuteDataFramePreprocessor().preprocess(self.nb, self.resources)
        ChangeOutputTypePreprocessor().preprocess(self.nb, self.resources)

    def to_md(self):
        me = MarkdownExporter(config={'NbConvertBase': {'display_data_priority': 
                                                        self.DISPLAY_DATA_PRIORITY}})
        md_data, self.resources = me.from_notebook_node(self.nb, self.resources)
        
        # the base64 encoded binary files are saved in output_resources
        image_data_dict = {**self.resources['outputs'], **self.resources['image_data_dict']}
        for filename, image_data in image_data_dict.items():
            new_filename = str(Path(self.image_dir_name) / filename)
            new_filename = urllib.parse.quote(new_filename)
            md_data = md_data.replace(filename, new_filename)

        if self.web_app:
            self.return_data['md_data'] = md_data
            self.return_data['md_images'] = image_data_dict
            self.return_data['image_dir_name'] = self.image_dir_name
        else:
            image_dir = self.final_nb_home / self.image_dir_name
            if image_dir.is_dir():
                shutil.rmtree(image_dir)
            image_dir.mkdir()

            for filename, value in image_data_dict.items():
                with open(image_dir / filename, 'wb') as f:
                    f.write(value)
            
            fn = self.final_nb_home / (self.document_name + '.md')
            with open(fn, mode='w') as f:
                f.write(md_data)

    def to_pdf_latex(self):
        if 'outputs' in self.resources:
            # remove outputs from MarkdownExporter if used
            self.resources.pop('outputs')
        
        # must download html images for latex to use them
        from ._preprocessors import MarkdownHTTPPreprocessor
        temp_dir = Path(self.td.name)
        self.resources['temp_dir'] = temp_dir
        MarkdownHTTPPreprocessor().preprocess(self.nb, self.resources)

        for filename, image_data in self.resources['image_data_dict'].items():
            fn_pieces = filename.split('_')
            cell_idx = int(fn_pieces[1])
            ext = fn_pieces[-1].split('.')[-1]
            new_filename = str(temp_dir / filename)

            # extract first image from gif and use as png for latex pdf
            if ext == 'gif':
                buffer = io.BytesIO(image_data)
                arr = mimage.imread(buffer, format='gif')
                new_filename = filename.split('.')[0] + '.png'
                new_filename = str(temp_dir / new_filename)
                mimage.imsave(new_filename, arr)
            else:
                with open(new_filename, 'wb') as f:
                    f.write(image_data)

            cell = self.nb.cells[cell_idx]
            cell['source'] = cell['source'].replace(filename, new_filename)

        pdf = PDFExporter(config={'NbConvertBase': {'display_data_priority': 
                                                     self.DISPLAY_DATA_PRIORITY}})
        pdf_data, self.resources = pdf.from_notebook_node(self.nb, self.resources)
        self.return_data['pdf_data'] = pdf_data
        if not self.web_app:
            fn = self.final_nb_home / (self.document_name + '.pdf')
            with open(fn, mode='wb') as f:
                f.write(pdf_data)

    def to_pdf_browser(self):
        from ._browser_pdf import BrowserExporter
        be = BrowserExporter()
        pdf_data, self.resources = be.from_notebook_node(self.nb, self.resources)
        self.return_data['pdf_data'] = pdf_data
        
        if not self.web_app:
            fn = self.final_nb_home / (self.document_name + '.pdf')
            with open(fn, mode='wb') as f:
                f.write(pdf_data)

    def save_notebook_to_file(self):
        if self.save_notebook:
            import copy
            nb = copy.deepcopy(self.nb)
            for cell in nb['cells']:
                if cell['cell_type'] == 'code':
                    for output in cell['outputs']:
                        data = output.get('data', {})
                        html = data.get('text/html', '')
                        if 'image/png' in data and '</table>' in html:
                            data.pop('text/html')

            name = self.nb_name + '_dataframe_image.ipynb'
            file = self.final_nb_home / name
            nbformat.write(nb, file)

    def convert(self):
        # Step 1: execute notebook if required
        self.execute_notebook()
        # Step 2: if exporting as pdf with browser, do this first
        # as it requires no other preprocessing
        if 'pdf_browser' in self.to:
            self.to_pdf_browser()
        
        if 'md' in self.to or 'pdf_latex' in self.to:
            # Step 3: If converting to markdown or latex_pdf, do no execute preprocessing
            # This will also change the output type for images with ChangeOutputTypePreprocessor
            self.no_execute_preprocess()
            # Step 4: Save notebook if necessary before processing markdown
            self.save_notebook_to_file()
            # Step 5: Preprocess markdown
            MarkdownPreprocessor().preprocess(self.nb, self.resources)
            # Step 6 Remove converter from resources - nbconvert cannot copy matplotlib transform object
            self.resources.pop('converter')
            # Step 7: Convert to markdown if required
            if 'md' in self.to:
                self.to_md()
            # Step 8: Convert to pdf via latex if required
            if 'pdf_latex' in self.to:
                self.to_pdf_latex()


def convert(filename, to='pdf', use='latex', center_df=True, max_rows=30, 
            max_cols=10, execute=False, save_notebook=False, limit=None, 
            document_name=None, table_conversion='chrome', chrome_path=None, 
            latex_command=None, output_dir=None):
    """
    Convert a Jupyter Notebook to pdf or markdown using images for pandas
    DataFrames instead of their normal latex/markdown representation. 
    The images will be screenshots of the DataFrames as they appear in a 
    chrome browser.

    By default, the new file will be created in the same directory where the 
    notebook resides and use the same name but with appropriate extension.

    When converting to markdown, a folder with the title 
    {notebook_name}_files will be created to hold all of the images.

    Caution, this is computationally expensive and takes a long time to 
    complete with many DataFrames. You may wish to begin by using the 
    `limit` parameter to convert just a few cells.

    Parameters
    ----------
    filename : str
        Path to Jupyter Notebook '.ipynb' file that you'd like to convert.

    to : str or list, default 'pdf'
        Choose conversion format. Either 'pdf' or 'markdown'/'md' or a 
        list with all formats.

    use : 'latex' or 'browser', default 'latex'
        Choose to convert using latex or chrome web browser when converting 
        to pdf. Output is significantly different for each. Use 'latex' when
        you desire a formal report. Use 'browser' to get output similar to
        that when printing to pdf within a chrome web browser.

    center_df : bool, default True
        Choose whether to center the DataFrames or not in the image. By 
        default, this is True, though in Jupyter Notebooks, they are 
        left-aligned. Use False to make left-aligned.

    max_rows : int, default 30
        Maximum number of rows to output from DataFrame. This is forwarded to 
        the `to_html` DataFrame method.

    max_cols : int, default 10
        Maximum number of columns to output from DataFrame. This is forwarded 
        to the `to_html` DataFrame method.

    execute : bool, default False
        Whether or not to execute the notebook first.

    save_notebook : bool, default False
        Whether or not to save the notebook with pandas DataFrames as images as 
        a new notebook. The filename will be '{notebook_name}_dataframe_image.ipynb'

    limit : int, default None
        Limit the number of cells in the notebook for conversion. This is 
        useful to test conversion of a large notebook on a smaller subset. 

    document_name : str, default None
        Name of newly created pdf/markdown document without the extension. If not
        provided, the current name of the notebook will be used.
    
    table_conversion : 'chrome' or 'matplotlib'
        DataFrames (and other tables) will be inserted in your document
        as an image using a screenshot from Chrome. If this doesn't
        work, use matplotlib, which will always work and produce
        similar results.

    chrome_path : str, default None
        Path to your machine's chrome executable. When None, it is 
        automatically found. Use this when chrome is not automatically found.

    latex_command: list, default None
        Pass in a list of commands that nbconvert will use to convert the 
        latex document to pdf. The latex document is created temporarily when
        converting to pdf with the `use` option set to 'latex'. By default,
        it is set to this list: ['xelatex', {filename}, 'quiet']

        If the xelatex command is not found on your machine, then pdflatex 
        will be substituted for it. You must have latex installed on your 
        machine for this to work. Get more info on how to install latex -
        https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex

    output_dir : str, default None
        Directory where new pdf and/or markdown files will be saved. By default, 
        this will be the same directory as the notebook. The directory 
        for images will also be created in here. If `save_notebook` is set to
        True, it will be saved here as well. Provide a relative or absolute path.
    """
    c = Converter(filename, to, use, center_df, max_rows, max_cols, execute, 
                  save_notebook, limit, document_name, table_conversion, chrome_path, 
                  latex_command, output_dir, web_app=False)
    c.convert()
