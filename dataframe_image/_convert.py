import base64
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import re
import io

import nbformat
from nbconvert import MarkdownExporter, PDFExporter
from nbconvert.preprocessors import ExecutePreprocessor
from traitlets.config import Config

from ._preprocessors import (MarkdownPreprocessor, 
                             NoExecuteDataFramePreprocessor, 
                             ChangeOutputTypePreprocessor)


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

        self.resources = self.get_resources()
        self.first = True

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
        if len(to) == 2:
            to = ['md', 'pdf']
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

    def get_resources(self):
        resources = {'metadata': {'path': str(self.nb_home), 
                                  'name': self.document_name},
                     'output_files_dir': self.image_dir_name}
        return resources

    def create_images_dir(self):
        images_home = self.final_nb_home / self.image_dir_name
        if images_home.is_dir():
            shutil.rmtree(images_home)
        images_home.mkdir()
        
    def get_code_to_run(self):
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
        return code

    def get_preprocessors(self, to, td=None):
        preprocessors = []

        # save images in markdown to either a temporary directory(pdf) 
        # or an actual directory(markdown)
        if to == 'pdf':
            td_path = Path(td.name)
            mp = MarkdownPreprocessor(output_dir=td_path, image_dir_name=td_path)
        elif to == 'md':
            mp = MarkdownPreprocessor(output_dir=self.final_nb_home / self.image_dir_name,
                                      image_dir_name=Path(self.image_dir_name))
        preprocessors.append(mp)

        if self.execute:
            code = self.get_code_to_run()
            extra_arguments = [f"--InteractiveShellApp.code_to_run='{code}'"]
            pp = ExecutePreprocessor(timeout=600, allow_errors=True, 
                                     extra_arguments=extra_arguments)
            preprocessors.append(pp)
        else:
            preprocessors.append(NoExecuteDataFramePreprocessor())

        preprocessors.append(ChangeOutputTypePreprocessor())
        return preprocessors

    def preprocess(self, preprocessors):
        for pp in preprocessors:
            self.nb, self.resources = pp.preprocess(self.nb, self.resources)
    
    def save_notebook_to_file(self):
        if self.save_notebook:
            name = self.nb_name + '_dataframe_image.ipynb'
            file = self.final_nb_home / name
            nbformat.write(self.nb, file)

    def to_pdf(self):
        if self.first:
            td = TemporaryDirectory()
            preprocessors = self.get_preprocessors('pdf', td=td)
            self.preprocess(preprocessors)

        pdf = PDFExporter(config={'NbConvertBase': {'display_data_priority': 
                                                    self.DISPLAY_DATA_PRIORITY}})

        pdf_data, self.resources = pdf.from_notebook_node(self.nb, self.resources)
        fn = self.final_nb_home / (self.document_name + '.pdf')
        with open(fn, mode='wb') as f:
            f.write(pdf_data)

    def to_md(self):
        if self.first:
            preprocessors = self.get_preprocessors('md')
            self.create_images_dir()
            self.preprocess(preprocessors)

        me = MarkdownExporter(config={'NbConvertBase': {'display_data_priority': 
                                                        self.DISPLAY_DATA_PRIORITY}})
        md_data, self.resources = me.from_notebook_node(self.nb, self.resources)
        # the base64 encoded binary files are saved in output_resources
        for filename, data in self.resources['outputs'].items():
            with open(self.final_nb_home / filename, 'wb') as f:
                f.write(data)
        fn = self.final_nb_home / (self.document_name + '.md')
        with open(fn, mode='w') as f:
            f.write(md_data)
        self.reset_resources()

    def reset_resources(self):
        self.first = False
        del self.resources['outputs']
        del self.resources['output_extension']

    def convert(self):
        for kind in self.to:
            getattr(self, f'to_{kind}')()
        self.save_notebook_to_file()


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
    {notebook_name}_files will be created to hold all of the images. Choose 
    the title of this folder with `image_dir_name`.

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
        Width of the screenshot in pixels. This may need to be increased for 
        larger monitors. If this value is too small, then smaller DataFrames will 
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
        Whether or not to execute the notebook first. When `False`, all HTML 
        tables in the output will be converted to images regardless if they 
        are dataframes or not.

    save_notebook : bool, default `False`
        Whether or not to save the notebook with pandas DataFrames as images as 
        a new notebook. The filename will be '{notebook_name}_dataframe_image.ipynb'

    output_dir: str, default `None`
        Directory where new pdf and/or markdown files will be saved. By default, 
        this will be the same directory as the notebook. The directory 
        for images will also be created in here. If `save_notebook` is set to
        True, it will be saved here as well.

        Provide a relative or absolute path.

    image_dir_name=str, default `None`
        The directory name to save the DataFrame images and any other images
        produced within the markdown or notebook code cells (i.e. plots). 
        
        Only created when converting to markdown. If created, will be saved
        within `output_dir`.
        
        By default, the directory name will be '{notebook_name}_files'.
        The images themselves will be given names such as output_1_0.png where 
        the first number represents the cell's execution number and the second 
        is the image number for that particular cell. A similar naming convention
        is used for markdown images.
    """
    c = Converter(filename, to, max_rows, max_cols, ss_width, ss_height, 
                  resize, chrome_path, limit, document_name, execute, 
                  save_notebook, output_dir, image_dir_name)
    c.convert()
