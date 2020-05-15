import argparse

DESCRIPTION = '''
===============\n\n\n\n
dataframe_image\n
===============\n\n
Embed pandas DataFrames as images when converting Jupyter Notebooks to pdf 
or markdown documents. 
'''

NOTEBOOK_HELP = '''The filename of the notebook you wish to convert'''

TO_HELP = '''Type of document to create - either pdf or markdown. Possible values are
        'pdf', 'markdown', and 'md'. Separate each value by 
        a comma to create multiple documents. i.e. use pdf,md to convert to both
        markdown and pdf.'''

MAX_ROWS_HELP = '''Type: %(type)s, Default: %(default)s\n\n
                    Maximum number of rows to output from DataFrame. This is forwarded to 
                   the `to_html` DataFrame method.'''

MAX_COLS_HELP = ''' 
        Type: %(type)s, Default: %(default)s
        Maximum number of columns to output from DataFrame. This is forwarded 
        to the `to_html` DataFrame method.'''

SS_WIDTH_HELP = '''
        Type: %(type)s, Default: %(default)s
        Width of the screenshot in pixels. This may need to be increased for 
        larger monitors. If this value is too small, then smaller DataFrames will 
        appear larger. It's best to keep this value at least as large as the 
        width of the output section of a Jupyter Notebook.'''

SS_HEIGHT_HELP = '''
        Type: %(type)s, Default: %(default)s
        Height of the screen shot. The height of the image is automatically 
        cropped so that only the relevant parts of the DataFrame are shown.
'''

RESIZE_HELP = '''
        Default: 1
        Relative resizing of image. Higher numbers produce smaller images. 
        The Pillow `Image.resize` method is used for this.
        '''

CHROME_PATH_HELP = '''
        Default: None
        Path to your machine's chrome executable. By default, it is 
        automatically found. Use this when chrome is not automatically found.
        '''

LIMIT_HELP = '''
        Limit the number of cells in the notebook for conversion. This is 
        useful to test conversion of a large notebook on a smaller subset. 
        '''

DOCUMENT_NAME_HELP = '''
        Name of newly created pdf/markdown document without the extension. If not
        provided, the name of the notebook will be used.
        '''

EXECUTE_HELP = '''
        Default: True
        Whether or not to execute the notebook first. When False, all HTML 
        tables in the output will be converted to images regardless if they 
        are dataframes or not.
        '''

SAVE_NOTEBOOK_HELP = '''
        Default: False
        Whether or not to save the notebook with pandas DataFrames as images as 
        a new notebook. The filename will be '{notebook_name}_dataframe_image.ipynb'
'''

OUTPUT_DIR_HELP = '''
        Directory where new pdf and/or markdown files will be saved. By default, 
        this will be in the same directory where the notebook is. The directory 
        for images will also be created in here. If --save-notebook is set to
        True, it will be saved here as well.

        Provide a relative path to the current working directory 
        or an absolute path.'''

IMAGE_DIR_HELP = '''
        The directory name to store the DataFrame images and any other images
        produced by the notebook code cells (i.e. plots). This image directory
        is only produced when creating a markdown document. It will be created
        within output_dir.

        By default, the name will be '{notebook_name}_files'.
        The images themselves will be given names such as output_1_0.png where 
        the first number represents the cell's execution number and the second 
        is the image number for that particular cell.
    '''


parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('filename', help=NOTEBOOK_HELP)
parser.add_argument('--to', type=str, choices=['md', 'pdf', 'md,pdf'], 
                    default='pdf', help=TO_HELP)
parser.add_argument('--max-rows', type=int, default=30, help=MAX_ROWS_HELP)
parser.add_argument('--max-cols', type=int, default=10, help=MAX_COLS_HELP)
parser.add_argument('--ss-width', type=int, default=1000, help=SS_WIDTH_HELP)
parser.add_argument('--ss-height', type=int, default=900, help=SS_HEIGHT_HELP)
parser.add_argument('--resize', type=float, default=1, help=RESIZE_HELP)
parser.add_argument('--chrome-path', help=CHROME_PATH_HELP)
parser.add_argument('--limit', type=int, help=LIMIT_HELP)
parser.add_argument('--document-name', help=DOCUMENT_NAME_HELP)
parser.add_argument('--execute', type=bool, default=True, help=EXECUTE_HELP)
parser.add_argument('--save-notebook', type=bool, default=False, help=SAVE_NOTEBOOK_HELP)
parser.add_argument('--output-dir', help=OUTPUT_DIR_HELP)
parser.add_argument('--image-dir-name', help=IMAGE_DIR_HELP)

def main():
    args = vars(parser.parse_args())
    from ._convert import convert
    convert(**args)
