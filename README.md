# dataframe_image

[![](https://img.shields.io/pypi/v/dataframe_image)](https://pypi.org/project/dataframe_image)
[![PyPI - License](https://img.shields.io/pypi/l/dataframe_image)](LICENSE)

A package to convert Jupyter Notebooks to PDF and/or Markdown embedding pandas DataFrames as images.

## Overview

When converting Jupyter Notebooks to pdf using nbconvert, pandas DataFrames appear as either raw text or as simple LaTeX tables. The left side of the image below shows this representation.

![png](https://github.com/dexplo/dataframe_image/raw/gh-pages/images/dataframe_image_compare.png)

This package was first created to embed DataFrames into pdf and markdown documents as images so that they appear exactly as they do in Jupyter Notebooks, as seen from the right side of the image above. It has since added much more functionality.

## Usage

Upon installation, the option `DataFrame as Image (PDF or Markdown)` will appear in the menu `File -> Download as`. Clicking this option will open up a new browser tab with a short form to be completed.

![png](https://github.com/dexplo/dataframe_image/raw/gh-pages/images/form.png)

### Exporting individual DataFrames

dataframe_image has the ability to export both normal and styled DataFrames as images from within a Python script. Pass your normal or styled DataFrame to the `export` function along with a file location to save it as an image.

```python
>>> import dataframe_image as dfi
>>> dfi.export(df_styled, 'df_styled.png')
```

You may also export directly from the DataFrame or styled DataFrame using the `dfi.export` and `export_png` methods, respectively.

```python
>>> df.dfi.export('df.png')
>>> df_styled.export_png('df_styled.png)
```

Here, an example of how exporting a DataFrame would look like in a notebook.

![png](https://github.com/dexplo/dataframe_image/raw/gh-pages/images/dfi_export.png)

## Installation

Install with either:

* `pip install dataframe_image`
* `conda install -c conda-forge dataframe_image`

## PDF Conversion - LaTeX vs Chrome Browser

By default, conversion to pdf happens via LaTeX, which you must have pre-installed on your machine. If you do not have the correct LaTeX installation, you'll need to select the Chrome Browser option to make the conversion.

Conversion via Chrome browser is much quicker and will look very different than the LaTeX rendition. The chrome browser version will look nearly the same as it does in your browser, while the LaTeX version looking more like a book/article.

Consult [nbconvert's documentation](https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex) to learn how to get latex installed correctly on your machine.

## More features

Below, is a description of other features from dataframe_image:

* Embeds all images from markdown cells (inline, reference, attachments, and `<img>` tags) into the pdf
* Saves the new documents anywhere in your filesystem and correctly link the resources
* Converts gifs to single-frame png files allowing them to be embedded into the pdf

## As a Python Library

dataframe_image can also be used outside of the notebook as a normal Python library. In a separate Python script, import the `dataframe_image` package and pass the file name of your notebook to the `convert` function.

```python
>>> import dataframe_image as dfi
>>> dfi.convert('path/to/your_notebook.ipynb',
                to='pdf',
                use='latex',
                center_df=True,
                max_rows=30,
                max_cols=10,
                execute=False,
                save_notebook=False,
                limit=None,
                document_name=None,
                table_conversion='chrome'
                chrome_path=None,
                latex_command=None,
                output_dir=None,
                )
```

By default, the new file(s) will be saved in the same directory where the notebook resides. Do not run this command within the same notebook that is being converted.

### From the Command Line

The command line tool `dataframe_image` will be available upon installation with the same options as the `convert` function from above.

```bash
dataframe_image --to=pdf "my notebook with dataframes.ipynb"
```

## Finding Google Chrome

You must have Google Chrome (or Brave) installed in order for dataframe_image to work. The path to Chrome should automatically be found. If Chrome is not in a standard location, set it with the `chrome_path` parameter.

### Using matplotlib instead of Chrome

If you do not have Chrome installed or cannot get it to work properly, you can alternatively use matplotlib to convert the DataFrames to images. Select this option by setting the `table_conversion` parameter to `'matplotlib'`.

## Publish to Medium

Closely related to this package is [`jupyter_to_medium`](https://github.com/dexplot/jupyter_to_medium), which publishes your notebooks directly and quickly as Medium blog posts.

## Dependencies

You must have the following Python libraries installed:

* [pandas](https://github.com/pandas-dev/pandas)
* [nbconvert](https://github.com/jupyter/nbconvert)
* [requests](https://requests.readthedocs.io/en/master/)
* [matplotlib](http://matplotlib.org/)
* [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
* [aiohttp](https://docs.aiohttp.org/en/stable/index.html)
