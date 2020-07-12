import pandas as pd

from ._screenshot import Screenshot


@pd.api.extensions.register_dataframe_accessor("dfi")
class _Export:

    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    def export(self, filename, fontsize=14, max_rows=None, max_cols=None, 
               table_conversion='chrome', chrome_path=None):
        """
        Export a DataFrame as png to a file

        Parameters
        ----------
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
            an error will be raised for DataFrames with more than 50 rows.
            Set this parameter explicitly to override this error. Use -1 for all rows.

        max_cols : int
            Maximum number of rows to output from DataFrame. This number is passed
            to the `to_html` DataFrame method.

            To prevent accidentally creating images with large numbers of columns,
            an error will be raised for DataFrames with more than 30 columns.
            Set this parameter explicitly to override this error. Use -1 for all columns.

        table_conversion : 'chrome' or 'matplotlib', default 'chrome'
            DataFrames will be converted to png via Chrome or matplotlib. Use chrome
            unless you cannot get it to work. matplotlib should provide a decent
            alternative.

        chrome_path : str, default `None`
            Path to your machine's chrome executable. When `None`, it is 
            automatically found. Use this when chrome is not automatically found.
        """
        if table_conversion == 'chrome':
            converter = Screenshot(max_rows=max_rows, max_cols=max_cols, chrome_path=chrome_path,
                                   ss_width=1000, ss_height=600, fontsize=fontsize, 
                                   encode_base64=False, limit_crop=False).run
        else:
            from ._matplotlib_table import TableMaker
            converter = TableMaker(fontsize=fontsize, encode_base64=False, for_document=False).run

        if self._obj.shape[0] > 50 and max_rows is None:
            raise ValueError('Your DataFrame has more than 50 rows and will produce a huge '
                             'image file, possibly causing your computer to crash. '
                             'Override this error by explicitly setting `max_rows`. '
                             'Use -1 for all rows.')
        if max_rows == -1:
            max_rows = None

        if self._obj.shape[1] > 30 and max_cols is None:
            raise ValueError('Your DataFrame has more than 30 columns and will produce a huge '
                             'image file, possibly causing your computer to crash. '
                             'Override this error by explicitly setting `max_cols`. '
                             'Use -1 for all columns.')

        if max_cols == -1:
            max_cols = None
        
        html = self._obj.to_html(max_rows=max_rows, max_cols=max_cols)
        img_str = converter(html)

        if isinstance(filename, str):
            open(filename, 'wb').write(img_str)
        elif hasattr(filename, 'write'):
            filename.write(img_str)
