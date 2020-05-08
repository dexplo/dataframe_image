# dataframe_image

A package to convert Jupyter Notebooks to either pdf or markdown documents embedding pandas DataFrames as images instead of their default format.

When converting Jupyter Notebooks to pdf using nbconvert, pandas DataFrames appear as either raw text or as a simple latex table. When converting to markdown The DataFrame's appearance while running a Jupyter Notebook is much different. Below, we have a pdf showing both the plain text and latex DataFrame representation.

![png](images/cur_nb.png)

This package was created to embed DataFrames into pdf and markdown documents as images so that they appear exactly as they do in a Jupyter Notebook. Here, the same DataFrame as above is show in a pdf converted using dataframe_image.

![png](images/ss_pdf.png)

## Installation

`pip install dataframe_image`

## Usage

In a separate Python script, import the `dataframe_image` package and pass the file name of your notebook to the `convert` function.

```python
>>> import dataframe_image as dfi
>>> dfi.convert('path/to/your_notebook.ipynb',
                to='pdf',
                max_rows=30,
                max_cols=10,
                ss_width=1000,
                ss_height=900,
                resize=1,
                chrome_path=None,
                limit=None
                )
```

## Dependencies

You must have the following python libraries installed

* [pandas](https://github.com/pandas-dev/pandas)
* [nbconvert](https://github.com/jupyter/nbconvert) with [xelatex installed](https://miktex.org/download)
* [pillow](https://github.com/python-pillow/Pillow)

You must also have Google Chrome installed.
