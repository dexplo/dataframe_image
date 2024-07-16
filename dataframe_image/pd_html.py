import pandas as pd
from packaging import version


def styler2html(style):
    """convert dataframe and sytler to html base on different pandas version"""
    if version.parse(pd.__version__) >= version.parse("1.4"):
        html = style.to_html()
    else:
        html = style.render()
    html_template = f"""<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en"><head><meta charset="UTF-8"/></head>{html}</html>"""
    return html_template
