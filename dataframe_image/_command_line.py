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

--latex_command
    Pass in a list of commands that nbconvert will use to convert the 
    latex document to pdf. The latex document is created temporarily when
    converting to pdf with the `use` option set to 'latex'.

    If the xelatex command is not found on your machine, then pdflatex 
    will be substituted for it. You must have latex installed on your 
    machine for this to work. Get more info on how to install latex -
    https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex
    (default: ['xelatex', {filename}, 'quiet'])

--max-rows
    Maximum number of rows to output from DataFrame. This is forwarded to 
    the `to_html` DataFrame method. (default: 30)

--max-cols
    Maximum number of columns to output from DataFrame. This is forwarded 
    to the `to_html` DataFrame method. (deault: 10)

--ss-width
    Width of the screenshot in pixels. This may need to be increased for 
    larger monitors. If this value is too small, then smaller DataFrames 
    will appear larger. It's best to keep this value at least as large as 
    the width of the output section of a Jupyter Notebook. (default: 1000)

--ss-height
    Height of the screen shot. The height of the image is automatically 
    cropped so that only the relevant parts of the DataFrame are shown.
    (default: 900)

--resize
    Relative resizing of image. Higher numbers produce smaller images. 
    The Pillow `Image.resize` method is used for this. (default: 1)

--chrome-path
    Path to your machine's chrome executable. By default, it is 
    automatically found. Use this when chrome is not automatically found.

--limit
    Limit the number of cells in the notebook for conversion. This is 
    useful to test conversion of a large notebook on a smaller subset.

--document-name
    Name of newly created pdf/markdown document without the extension. 
    If not provided, the name of the notebook will be used.

--execute
    Whether or not to execute the notebook first. When False, all HTML 
    tables in the output will be converted to images regardless if they 
    are dataframes or not. (default: True)

--save-notebook
    Whether or not to save the notebook with DataFrames as images as a new 
    notebook. The filename will be '{notebook_name}_dataframe_image.ipynb'
    (default: False)

--output-dir
    Directory where new pdf and/or markdown files will be saved. By default,
    this will be in the same directory where the notebook is. The directory 
    for images will also be created in here. If --save-notebook is set to
    True, it will be saved here as well.

    Provide a relative path to the current working directory 
    or an absolute path.

--image-dir
    The directory name to store the DataFrame images and any other images
    produced by the notebook code cells (i.e. plots). This image directory
    is only produced when creating a markdown document. It will be created
    within output_dir.

    By default, the name will be '{notebook_name}_files'.
    The images themselves will be given names such as output_1_0.png where 
    the first number represents the cell's execution number and the second 
    is the image number for that particular cell.


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
parser.add_argument('--latex-command', type=list, default=['xelatex', '{filename}', 'quiet'])
parser.add_argument('--max-rows', type=int, default=30)
parser.add_argument('--max-cols', type=int, default=10)
parser.add_argument('--ss-width', type=int, default=1000)
parser.add_argument('--ss-height', type=int, default=900)
parser.add_argument('--resize', type=float, default=1)
parser.add_argument('--chrome-path')
parser.add_argument('--limit', type=int)
parser.add_argument('--document-name')
parser.add_argument('--execute', type=bool, default=True)
parser.add_argument('--save-notebook', type=bool, default=False)
parser.add_argument('--output-dir')
parser.add_argument('--image-dir-name')

def main():
    if len(sys.argv) == 1 or '-h' in sys.argv or '--help' in sys.argv:
        print(HELP)
    else:
        args = vars(parser.parse_args())
        del args['help']
        from ._convert import convert
        convert(**args)
