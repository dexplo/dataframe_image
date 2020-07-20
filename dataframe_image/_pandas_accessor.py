import pandas as pd
from pandas.io.formats.style import Styler

from ._screenshot import Screenshot

MAX_COLS = 30
MAX_ROWS = 100


@pd.api.extensions.register_dataframe_accessor("dfi")
class _Export:

    def __init__(self, df):
        self._df = df

    def export(self, filename, fontsize=14, max_rows=None, max_cols=None, 
               table_conversion='chrome', chrome_path=None):
        return _export(self._df, filename, fontsize, max_rows, max_cols, 
                       table_conversion, chrome_path)


def export(obj, filename, fontsize=14, max_rows=None, max_cols=None, 
               table_conversion='chrome', chrome_path=None):
        return _export(obj, filename, fontsize, max_rows, max_cols, table_conversion, chrome_path)
        

def _export(obj, filename, fontsize, max_rows, max_cols, table_conversion, chrome_path):    
    is_styler = isinstance(obj, Styler)
    df = obj.data if is_styler else obj

    if table_conversion == 'chrome':
        converter = Screenshot(max_rows=max_rows, max_cols=max_cols, chrome_path=chrome_path,
                               fontsize=fontsize, encode_base64=False, limit_crop=False).run
    else:
        from ._matplotlib_table import TableMaker
        converter = TableMaker(fontsize=fontsize, encode_base64=False, for_document=False).run

    if df.shape[0] > MAX_ROWS and max_rows is None:
        error_msg = (f'Your DataFrame has more than {MAX_ROWS} rows and will produce a huge '
                    'image file, possibly causing your computer to crash. Override this error '
                    'by explicitly setting `max_rows`. Use -1 for all rows.')
        if is_styler:
            error_msg = (f'Your Styled DataFrame has more than {MAX_ROWS} rows and will produce '
                        'a huge image file, possibly causing your computer to crash. Override '
                        'this error by explicitly setting `max_rows` to -1 for all columns. '
                        'Styled DataFrames are unable to select a subset of rows or columns '
                        'and therefore do not work with the `max_rows` and `max_cols` parameters')
        raise ValueError(error_msg)
    if max_rows == -1:
        max_rows = None

    if df.shape[1] > MAX_COLS and max_cols is None:
        error_msg = (f'Your DataFrame has more than {MAX_COLS} columns and will produce a huge '
                    'image file, possibly causing your computer to crash. Override this error '
                    'by explicitly setting `max_cols`. Use -1 for all columns.')
        if is_styler:
            error_msg = (f'Your Styled DataFrame has more than {MAX_COLS} columns and will '
                        'produce a huge image file, possibly causing your computer to crash. '
                        'Override this error by explicitly setting `max_cols` to -1 for '
                        'all columns. Styled DataFrames are unable to select a subset of '
                        'rows or columns and therefore do not work with the `max_rows` '
                        'and `max_cols` parameters')
        raise ValueError(error_msg)

    if max_cols == -1:
        max_cols = None

    if is_styler:
        html = '<div>' + obj.render() + '</div>'
    else:
        html = obj.to_html(max_rows=max_rows, max_cols=max_cols, notebook=True)
    
    img_str = converter(html)

    if isinstance(filename, str):
        open(filename, 'wb').write(img_str)
    elif hasattr(filename, 'write'):
        filename.write(img_str)

setattr(Styler, 'export_png', export)

accessor_intro = """
Export a DataFrame as png to a file

Parameters
----------"""

styler_intro = """
Export a styled DataFrame as png to a file

Parameters
----------"""

doc_params =f"""
filename : str or file-like
    The file location where the image will be saved. Provide a string 
    to specify a file location on your local machine or a file-like object 
    that has a `write` method.

fontsize : int
    Font size in points

max_rows : int
    Maximum number of rows to output from DataFrame. This number is passed
    to the `to_html` DataFrame method.

    To prevent accidentally creating images with large numbers of rows,
    an error will be raised for DataFrames with more than {MAX_ROWS} rows.
    Set this parameter explicitly to override this error. Use -1 for all rows.

max_cols : int
    Maximum number of rows to output from DataFrame. This number is passed
    to the `to_html` DataFrame method.

    To prevent accidentally creating images with large numbers of columns,
    an error will be raised for DataFrames with more than {MAX_COLS} columns.
    Set this parameter explicitly to override this error. Use -1 for all columns.

table_conversion : 'chrome' or 'matplotlib', default 'chrome'
    DataFrames will be converted to png via Chrome or matplotlib. Use chrome
    unless you cannot get it to work. matplotlib provides a decent
    alternative.

chrome_path : str, default `None`
    Path to your machine's chrome executable. When `None`, it is 
    automatically found. Use this when chrome is not automatically found.

"""

export_intro ="""
Export a DataFrame or Styled DataFrame as a png to a file.

Styled DataFrames cannot use max_rows or max_cols and 
cannot be exported with `table_conversion` set to 'matplotlib'.

Parameters
----------
obj : DataFrame or Styler object
    Object to export as an image
"""

_Export.export.__doc__ = accessor_intro + doc_params
export.__doc__ = export_intro + doc_params
Styler.export_png.__doc__ = styler_intro + doc_params
