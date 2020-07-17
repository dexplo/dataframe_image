import argparse
import textwrap
import sys

class CustomFormatter(argparse.RawTextHelpFormatter):
    pass

HELP = '''\n\n
          ========================================================

                              dataframe_image
        
          ========================================================

Embed pandas DataFrames as images when converting Jupyter Notebooks to 
pdf or markdown documents. 

Required Positional Arguments
=============================
filename
    The filename of the notebook you wish to convert

Optional Keyword Arguments
==========================
--to
    Type of document to create - either pdf or markdown. Possible values 
    are 'pdf', 'markdown', and 'md'. (default: pdf)

--use 
    Possible options are 'latex' or 'browser'.
    Choose to convert using latex or chrome web browser when converting 
    to pdf. Output is significantly different for each. Use 'latex' when
    you desire a formal report. Use 'browser' to get output similar to
    that when printing to pdf within a chrome web browser.
    (default: latex)

--center-df
    Choose whether to center the DataFrames or not in the image. By 
    default, this is True, though in Jupyter Notebooks, they are 
    left-aligned. Use False to make left-aligned. (default: True)

--max-rows
    Maximum number of rows to output from DataFrame. This is forwarded to 
    the `to_html` DataFrame method. (default: 30)

--max-cols
    Maximum number of columns to output from DataFrame. This is forwarded 
    to the `to_html` DataFrame method. (deault: 10)

--execute
    Whether or not to execute the notebook first. (default: False)

--save-notebook
    Whether or not to save the notebook with DataFrames as images as a new 
    notebook. The filename will be '{notebook_name}_dataframe_image.ipynb'
    (default: False)

--limit
    Limit the number of cells in the notebook for conversion. This is 
    useful to test conversion of a large notebook on a smaller subset.

--document-name
    Name of newly created pdf/markdown document without the extension. 
    If not provided, the name of the notebook will be used.

--table-conversion
    DataFrames (and other tables) will be inserted in your document
    as an image using a screenshot from Chrome. If this doesn't
    work, use matplotlib, which will always work and produce
    similar results.
    Valid values are 'chrome' or 'matplotlib' (default: 'chrome')

--chrome-path
    Path to your machine's chrome executable. By default, it is 
    automatically found. Use this when chrome is not automatically found.

--latex-command
    Pass in a list of commands that nbconvert will use to convert the 
    latex document to pdf. The latex document is created temporarily when
    converting to pdf with the `use` option set to 'latex'.

    If the xelatex command is not found on your machine, then pdflatex 
    will be substituted for it. You must have latex installed on your 
    machine for this to work. Get more info on how to install latex -
    https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex
    (default: ['xelatex', {filename}, 'quiet'])

--output-dir
    Directory where new pdf and/or markdown files will be saved. By default,
    this will be in the same directory where the notebook is. The directory 
    for images will also be created in here. If --save-notebook is set to
    True, it will be saved here as well. Provide a relative path to the 
    current working directory or an absolute path.


Examples
========

dataframe_image my_notebook.ipynb --to=pdf --save-notebook=True --execute=True

dataframe_image path/to/my_notebook.ipynb --to=md --output-dir="some other/directory/"

Created by Ted Petrou (https://www.dunderdata.com)

'''

parser = argparse.ArgumentParser(formatter_class=CustomFormatter, add_help=False, usage=argparse.SUPPRESS)
parser.add_argument('filename', default=False)
parser.add_argument('-h', '--help', action='store_true', dest='help')
parser.add_argument('--to', type=str, choices=['md', 'pdf', 'markdown'], default='pdf')
parser.add_argument('--use', type=str, choices=['latex', 'browser'], default='latex')
parser.add_argument('--center-df', type=bool, default=True)
parser.add_argument('--max-rows', type=int, default=30)
parser.add_argument('--max-cols', type=int, default=10)
parser.add_argument('--execute', type=bool, default=False)
parser.add_argument('--save-notebook', type=bool, default=False)
parser.add_argument('--limit', type=int)
parser.add_argument('--document-name')
parser.add_argument('--table-conversion', type=str, choices=['chrome', 'matplotlib'], default='chrome')
parser.add_argument('--chrome-path')
parser.add_argument('--latex-command', type=list, default=['xelatex', '{filename}', 'quiet'])
parser.add_argument('--output-dir')

def main():
    if len(sys.argv) == 1 or '-h' in sys.argv or '--help' in sys.argv:
        print(HELP)
    else:
        args = vars(parser.parse_args())
        del args['help']
        from ._convert import convert
        convert(**args)
