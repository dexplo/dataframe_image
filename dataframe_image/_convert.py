import base64
from pathlib import Path
import shutil
import re
import io

import nbformat
from nbconvert import MarkdownExporter, PDFExporter

from ._preprocessors import (MarkdownPreprocessor, 
                             NoExecuteDataFramePreprocessor, 
                             ChangeOutputTypeExecutePreprocessor)


class Converter:
    KINDS = ['pdf', 'md', 'markdown']
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

    def __init__(self, filename, to, max_rows, max_cols, ss_width, ss_height, resize, 
                 chrome_path, limit, document_name, execute, save_notebook, output_dir, 
                 image_dir_name):
        self.filename = Path(filename)
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.ss_width = ss_width
        self.ss_height = ss_height
        self.resize = resize
        self.chrome_path = chrome_path

        self.nb_home = self.filename.parent
        self.nb_name = self.filename.stem
        self.to = self.get_to(to)
        self.nb = self.get_notebook(limit)

        self.document_name = self.get_document_name(document_name)
        self.execute = execute
        self.save_notebook = save_notebook
        self.final_nb_home = self.get_new_notebook_home(output_dir)
        self.image_dir_name = self.get_image_dir_name(image_dir_name)

    def get_to(self, to):
        if isinstance(to, str):
            to = [to]
        elif not isinstance(to, list):
            raise TypeError('`to` must either be a string or a list. '
                            'Possible values are "pdf" and "md"')
        to = set(to)
        if 'markdown' in to:
            to.remove('markdown')
            to.add('md')
        for kind in to:
            if kind not in self.KINDS:
                raise TypeError(
                    "`to` must either be a string or a list. "
                    'Possible values are "pdf" or "markdown"/"md"'
                    ' and not {kind}.'
                )
        return to

    def get_notebook(self, limit):
        with open(self.filename) as f:
            nb = nbformat.read(f, as_version=4)

        if isinstance(limit, int):
            nb["cells"] = nb["cells"][:limit]

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

    def get_image_dir_name(self, image_dir_name):
        if image_dir_name:
            return image_dir_name
        else:
            return self.nb_name + '_files'

    def create_images_dir(self):
        images_home = self.final_nb_home / self.image_dir_name
        if images_home.is_dir():
            shutil.rmtree(images_home)
        images_home.mkdir()

    def process_markdown(self):
        mp = MarkdownPreprocessor(self.nb_home, self.final_nb_home, self.image_dir_name)
        self.nb, resources = mp.preprocess(self.nb, {})

    def execute_notebook(self):
        code = (
            "import pandas as pd;"
            "from dataframe_image._screenshot import make_repr_png;"
            f"_repr_png_ = make_repr_png(max_rows={self.max_rows}, "
            f"max_cols={self.max_cols}, ss_width={self.ss_width}, "
            f"ss_height={self.ss_height}, resize={self.resize}, "
            f"chrome_path={self.chrome_path});"
            "pd.DataFrame._repr_png_ = _repr_png_;"
            "from pandas.io.formats.style import Styler;"
            "Styler._repr_png_ = _repr_png_;"
            "del make_repr_png, _repr_png_"
        )
        extra_arguments = [f"--InteractiveShellApp.code_to_run='{code}'"]
        self.ep = ChangeOutputTypeExecutePreprocessor(timeout=600, allow_errors=True,
                                                      extra_arguments=extra_arguments)
        resources = {'metadata': {'path': str(self.nb_home)},
                     'output_files_dir': self.image_dir_name}
        self.nb, resources = self.ep.preprocess(self.nb, resources)

    def no_execute_notebook(self):
        nep = NoExecuteDataFramePreprocessor()
        resources = {'output_files_dir': self.image_dir_name}
        self.nb, resources = nep.preprocess(self.nb, resources)

    def save_notebook_to_file(self):
        if self.save_notebook:
            name = self.nb_name + '_dataframe_image.ipynb'
            file = self.final_nb_home / name
            nbformat.write(self.nb, file)

    def to_pdf(self):
        pdf = PDFExporter(config={"NbConvertBase": {"display_data_priority": 
                                                    self.DISPLAY_DATA_PRIORITY}})
        # nbconvert requires the absolute path for pdf exporting
        resources = {'metadata': {'path': str(self.final_nb_home.resolve()),
                                  'name': self.document_name},
                     'output_files_dir': self.image_dir_name}
        pdf_data, output_resources = pdf.from_notebook_node(self.nb, resources)
        fn = self.final_nb_home / (self.document_name + '.pdf')
        with open(fn, mode="wb") as f:
            f.write(pdf_data)

    def to_md(self):
        # this relative path gets prepended to the image filename
        resources = {'output_files_dir': self.image_dir_name}
        me = MarkdownExporter(config={"NbConvertBase": {"display_data_priority": 
                                                        self.DISPLAY_DATA_PRIORITY}})
        md_data, output_resources = me.from_notebook_node(self.nb, resources)

        # the base64 encoded binary files are saved in output_resources
        for filename, data in output_resources["outputs"].items():
            with open(self.final_nb_home / filename, "wb") as f:
                f.write(data)
        fn = self.final_nb_home / (self.document_name + '.md')
        with open(fn, mode="w") as f:
            f.write(md_data)

    def convert(self):
        self.create_images_dir()
        self.process_markdown()
        if self.execute:
            self.execute_notebook()
        else:
            self.no_execute_notebook()
        self.save_notebook_to_file()
        for kind in self.to:
            getattr(self, f"to_{kind}")()


def convert(filename, to='pdf', max_rows=30, max_cols=10, ss_width=1000, ss_height=900,
            resize=1, chrome_path=None, limit=None, document_name=None, execute=True, 
            save_notebook=False, output_dir=None, image_dir_name=None):
    """
    Convert a Jupyter Notebook to pdf or markdown using images for pandas
    DataFrames instead of their normal latex/markdown representation. 
    The images will be screenshots of the DataFrames as they appear in a 
    chrome browser.

    By default, the new file will be in the same directory where the 
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

    max_rows : int, default 30
        Maximum number of rows to output from DataFrame. This is forwarded to 
        the `to_html` DataFrame method.

    max_cols : int, default 10
        Maximum number of columns to output from DataFrame. This is forwarded 
        to the `to_html` DataFrame method.

    ss_width : int, default 1000
        Width of the screenshot. This may need to be increased for larger 
        monitors. If this value is too small, then smaller DataFrames will 
        appear larger. It's best to keep this value at least as large as the 
        width of the output section of a Jupyter Notebook.

    ss_height : int, default 900
        Height of the screen shot. The height of the image is automatically 
        cropped so that only the relevant parts of the DataFrame are shown.

    resize : int or float, default 1
        Relative resizing of image. Higher numbers produce smaller images. 
        The Pillow `Image.resize` method is used for this.

    chrome_path : str, default `None`
        Path to your machine's chrome executable. When `None`, it is 
        automatically found. Use this when chrome is not automatically found.

    limit : int, default `None`
        Limit the number of cells in the notebook for conversion. This is 
        useful to test conversion of a large notebook on a smaller subset. 

    document_name : str, default `None`
        Name of newly created pdf/markdown document without the extension. If not
        provided, the current name of the notebook will be used.

    execute : bool, default `True`
        Whether or not to execute the notebook first. Even if the notebook is 
        already executed, this must be re-executed in order for the dataframes 
        to appear as images.

    save_notebook : bool, default `False`
        Whether or not to save the notebook with pandas DataFrames as images as 
        a new notebook. The filename will be '{notebook_name}_dataframe_image.ipynb'

    output_dir: str, default `None`
        Directory where new pdf and/or markdown files will be saved. By default, 
        this will be in the same directory where the notebook is. The directory 
        for images will also be created in here. If --save-notebook is set to
        True, it will be saved here as well.

        Provide a relative path to the current working directory 
        or an absolute path.

    image_dir_name=str, default `None`
        The directory name to save the DataFrame images and any other images
        produced by the notebook code cells (i.e. plots). This image directory
        is only produced when creating a markdown document. It will be created
        within output_dir.
        
        By default, the directory name will be '{notebook_name}_files'.
        The images themselves will be given names such as output_1_0.png where 
        the first number represents the cell's execution number and the second 
        is the image number for that particular cell.
    """
    c = Converter(filename, to, max_rows, max_cols, ss_width, ss_height, 
                  resize, chrome_path, limit, document_name, execute, 
                  save_notebook, output_dir, image_dir_name)
    c.convert()
