import pandas as pd
from packaging import version


def styler2html(style):
    """convert dataframe and sytler to html base on different pandas version"""
    if version.parse(pd.__version__) >= version.parse("1.4"):
        html = style.to_html()
    else:
        html = style.render()
    return html
