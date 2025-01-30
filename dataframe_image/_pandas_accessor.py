import inspect
import io
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import pandas as pd
from pandas.io.formats.style import Styler
from PIL import Image

from dataframe_image.converter.browser import (
    AsyncPlayWrightConverter,
    ChromeConverter,
    Html2ImageConverter,
    PlayWrightConverter,
    SeleniumConverter,
)
from dataframe_image.logger import logger
from dataframe_image.pd_html import styler2html

MAX_COLS = 30
MAX_ROWS = 100




@contextmanager
def disable_max_image_pixels():
    pre_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None
    yield
    Image.MAX_IMAGE_PIXELS = pre_limit

@pd.api.extensions.register_dataframe_accessor("dfi")
class _Export:
    def __init__(self, df):
        self._df = df

    def export(
        self,
        filename,
        fontsize=14,
        max_rows=None,
        max_cols=None,
        table_conversion="chrome",
        chrome_path=None,
        dpi=None,
    ):
        return export(
            self._df,
            filename,
            fontsize,
            max_rows,
            max_cols,
            table_conversion,
            chrome_path,
            dpi,
        )


BROWSER_CONVERTER_DICT = {
    "chrome": ChromeConverter,
    "selenium": SeleniumConverter,
    "html2image": Html2ImageConverter,
    "playwright": PlayWrightConverter,
    "playwright_async": AsyncPlayWrightConverter,
}


def prepare_converter(
    filename,
    fontsize=14,
    max_rows=None,
    max_cols=None,
    table_conversion: Literal[
        "chrome", "matplotlib", "html2image", "playwright", "selenium", "playwright_async"
    ] = "playwright",
    chrome_path=None,
    dpi=None,
    use_mathjax=False,
    crop_top=True,
):
    if table_conversion in BROWSER_CONVERTER_DICT:
        converter = BROWSER_CONVERTER_DICT[table_conversion](
            max_rows=max_rows,
            max_cols=max_cols,
            chrome_path=chrome_path,
            fontsize=fontsize,
            encode_base64=False,
            crop_top=crop_top,
            device_scale_factor=(1 if dpi is None else dpi / 100.0),
            use_mathjax=use_mathjax,
        ).run
    else:
        from .converter.matplotlib_table import MatplotlibTableConverter

        # get extension from filename without dot
        if isinstance(filename, io.IOBase):
            extension = "png"
        else:
            extension = Path(filename).suffix

        if extension.startswith("."):
            extension = extension[1:]
        converter = MatplotlibTableConverter(
            fontsize=fontsize,
            encode_base64=False,
            for_document=False,
            savefig_dpi=dpi,
            format=extension,
        ).run

    return converter


def generate_html(
    obj: pd.DataFrame,
    filename,
    max_rows=None,
    max_cols=None,
):
    is_styler = isinstance(obj, Styler)
    df = obj.data if is_styler else obj
    if df.shape[0] > MAX_ROWS and max_rows is None:
        error_msg = (
            f"Your DataFrame has more than {MAX_ROWS} rows and will produce a huge "
            "image file, possibly causing your computer to crash. Override this error "
            "by explicitly setting `max_rows`. Use -1 for all rows."
        )
        if is_styler:
            error_msg = (
                f"Your Styled DataFrame has more than {MAX_ROWS} rows and will produce "
                "a huge image file, possibly causing your computer to crash. Override "
                "this error by explicitly setting `max_rows` to -1 for all columns. "
                "Styled DataFrames are unable to select a subset of rows or columns "
                "and therefore do not work with the `max_rows` and `max_cols` parameters"
            )
        raise ValueError(error_msg)

    if df.shape[1] > MAX_COLS and max_cols is None:
        error_msg = (
            f"Your DataFrame has more than {MAX_COLS} columns and will produce a huge "
            "image file, possibly causing your computer to crash. Override this error "
            "by explicitly setting `max_cols`. Use -1 for all columns."
        )
        if is_styler:
            error_msg = (
                f"Your Styled DataFrame has more than {MAX_COLS} columns and will "
                "produce a huge image file, possibly causing your computer to crash. "
                "Override this error by explicitly setting `max_cols` to -1 for "
                "all columns. Styled DataFrames are unable to select a subset of "
                "rows or columns and therefore do not work with the `max_rows` "
                "and `max_cols` parameters"
            )
        raise ValueError(error_msg)

    if max_rows == -1:
        max_rows = None

    if max_cols == -1:
        max_cols = None

    if is_styler:
        html = styler2html(obj)
    else:
        html = obj.to_html(max_rows=max_rows, max_cols=max_cols, notebook=True)
    # wrap html with a div and add id `dfi_table`
    html = f'<div id="dfi_table">{html}</div>'
    return html


def save_image(img_str, filename):

    try:
        with open(filename, "wb") as f:
            f.write(img_str)
    except TypeError as ex:
        if hasattr(filename, "write"):
            filename.write(img_str)
        else:
            raise ex
        
def export(
    obj: pd.DataFrame,
    filename,
    fontsize=14,
    max_rows=None,
    max_cols=None,
    table_conversion: Literal[
        "chrome", "matplotlib", "html2image", "playwright", "selenium"
    ] = "playwright",
    chrome_path=None,
    dpi=None,
    use_mathjax=False,
    crop_top=True,
):
    """export a DataFrame as png to a file

    Args:
        obj: DataFrame or Styler object, required
        filename: str or file-like, required
        fontsize: int, optional, default 14
        max_rows: int, optional, default None
        max_cols: int, optional, default None
        table_conversion: str, optional, default 'chrome'
        chrome_path: str, optional, default None
        dpi: int, optional, default None
        use_mathjax: bool, optional, default False
        crop_top: bool, optional, crop top of the generate image, default True
    """
    converter = prepare_converter(
        filename,
        fontsize,
        max_rows,
        max_cols,
        table_conversion,
        chrome_path,
        dpi,
        use_mathjax,
        crop_top=crop_top,
    )
    html = generate_html(obj, filename, max_rows, max_cols)

    with disable_max_image_pixels():
        img_str = converter(html)

    save_image(img_str, filename)


async def export_async(
    obj: pd.DataFrame,
    filename,
    fontsize=14,
    max_rows=None,
    max_cols=None,
    table_conversion: Literal[
        "chrome", "matplotlib", "html2image", "playwright", "selenium", "playwright_async"
    ] = "playwright",
    chrome_path=None,
    dpi=None,
    use_mathjax=False,
    crop_top=True,
):
    """export a DataFrame as png to a file

    Args:
        obj: DataFrame or Styler object, required
        filename: str or file-like, required
        fontsize: int, optional, default 14
        max_rows: int, optional, default None
        max_cols: int, optional, default None
        table_conversion: str, optional, default 'chrome'
        chrome_path: str, optional, default None
        dpi: int, optional, default None
        use_mathjax: bool, optional, default False
        crop_top: bool, optional, crop top of the generate image, default True
    """
    if table_conversion == "playwright_async":
        # show DeprecationWarning
        import warnings
        warnings.warn(
            "table_conversion='playwright_async' is deprecated, use 'playwright' instead",
            DeprecationWarning,
        )

    async_converters = ["playwright"]
    if table_conversion in async_converters:
        table_conversion = f"{table_conversion}_async"
    converter = prepare_converter(
        filename,
        fontsize,
        max_rows,
        max_cols,
        table_conversion,
        chrome_path,
        dpi,
        use_mathjax,
        crop_top=crop_top,
    )
    html = generate_html(obj, filename, max_rows, max_cols)
    with disable_max_image_pixels():
        # check if converter is async
        if inspect.iscoroutinefunction(converter):
            img_str = await converter(html)
        else:
            img_str = converter(html)
    # TODO: use async file writing
    save_image(img_str, filename)


setattr(Styler, "export_png", export)

accessor_intro = """
Export a DataFrame as png to a file

Parameters
----------"""

styler_intro = """
Export a styled DataFrame as png to a file

Parameters
----------"""

doc_params = f"""
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

dpi : int, default `None`
    Dots per inch - Use this to change the resolution ("quality") of the image.
    
    If `table_conversion`=`matplotlib`, this value is directly passed to 
    the "savefig" method. When `None`, the figure's DPI is used.
     
    If `table_conversion`=`chrome`, the dpi value is converted to a 
    "device scale factor" but should provide the same effect. When `None`,
    the "device scale factor" is 1.
use_mathjax : bool, default False
    Use MathJax to render LaTeX in the DataFrame. This only works with 
    `table_conversion` set to 'playwright', 'matplotlib' or 'selenium'.
crop_top : bool, default True
    Crop the top of the generated image. This is useful when the DataFrame
    has a lot of white space at the top of the image. But if you can set it
    to False if you think the image is being cropped too much.
"""

export_intro = """
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
