import sys
def main():
    args = sys.argv
    if len(args) == 1:
        get_help()

def get_help():
    s = '''
    ===============
    dataframe_image
    ===============

    Embed pandas DataFrames as images when converting Jupyter Notebooks to pdf 
    or markdown documents. 

    Usage
    =====
    dataframe_image [OPTIONS] <your_notebook.ipynb>

    Place the notebook name as the last argument.

    Options
    =======
    --to=<Unicode>
        Default: pdf
        Type of document to create - either pdf or markdown. Possible values are
        'pdf', 'markdown', and 'md'. Separate each value by 
        a comma to create multiple documents. i.e. use pdf,md to convert to both
        markdown and pdf.

    --max-rows=<Int>
        Default: 30
        Maximum number of rows to output from DataFrame. This is forwarded to 
        the `to_html` DataFrame method.

    --max-cols=<Int>
        Default: 10
        Maximum number of columns to output from DataFrame. This is forwarded 
        to the `to_html` DataFrame method.

    --ss-width=<Int>
        Default: 1000
        Width of the screenshot in pixels. This may need to be increased for 
        larger monitors. If this value is too small, then smaller DataFrames will 
        appear larger. It's best to keep this value at least as large as the 
        width of the output section of a Jupyter Notebook.

    --ss-height=<Int>
        Default: 900
        Height of the screen shot. The height of the image is automatically 
        cropped so that only the relevant parts of the DataFrame are shown.

    --resize=<IntOrFloat>
        Default: 1
        Relative resizing of image. Higher numbers produce smaller images. 
        The Pillow `Image.resize` method is used for this.

    --chrome-path=<Unicode>
        Default: ''
        Path to your machine's chrome executable. By default, it is 
        automatically found. Use this when chrome is not automatically found.

    --limit=<Int>
        Default: None
        Limit the number of cells in the notebook for conversion. This is 
        useful to test conversion of a large notebook on a smaller subset. 

    --document-name=<Unicode>
        Default: ''
        Name of newly created pdf/markdown document without the extension. If not
        provided, the name of the notebook will be used.

    --execute=<Bool>
        Default: True
        Whether or not to execute the notebook first. Even if the notebook is 
        already executed, this must be re-executed in order to hook into the 
        pandas DataFrame _repr_png_ function.

    --save-notebook=<Bool>
        Default: False
        Whether or not to save the notebook with pandas DataFrames as images as 
        a new notebook. The filename will be '{notebook_name}_dataframe_image.ipynb'

    --output-dir=<Unicode>
        Default: ''
        Directory where new pdf and/or markdown files will be saved. By default, 
        this will be in the same directory where the notebook is. The directory 
        for images will also be created in here. If --save-notebook is set to
        True, it will be saved here as well.

        Provide a relative path to the current working directory 
        or an absolute path.

    --image-dir-name=<Unicode>
        Default: ''
        The directory name to store the DataFrame images and any other images
        produced by the notebook code cells (i.e. plots). This image directory
        is only produced when creating a markdown document. It will be created
        within output_dir.

        By default, the name will be '{notebook_name}_files'.
        The images themselves will be given names such as output_1_0.png where 
        the first number represents the cell's execution number and the second 
        is the image number for that particular cell.
    '''
    print(s)
