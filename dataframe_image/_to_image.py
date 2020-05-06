import base64
import io
import numpy as np
from PIL import Image
from tempfile import NamedTemporaryFile
from subprocess import run
import pandas as pd

CSS = """<style>
table {
    background-color: transparent;
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    margin-left:0;
    margin-right:0;
    border:none;
    border-collapse: collapse;
    border-spacing:0;
    color:black;
    font-size:18px;
    table-layout:fixed;
    }
thead {
    border-bottom:1px solid black;vertical-align:bottom;
    }
tr, th, td {
    text-align:right;
    vertical-align: middle;
    padding:0.5em 0.5em;
    line-height:normal;
    white-space:normal;
    max-width:none;
    border:none;
    }
th {
    font-weight:bold; 
    text-align:left;
    }
tbody tr:nth-child(odd){
    background:#f5f5f5;
    }
    :link{
    text-decoration:underline;
}
</style>
"""

print(__file__)

def f(self):
    
    rows = min(pd.get_option('display.max_rows'), 30)
    html = CSS + self.to_html(max_cols=10, max_rows=rows, notebook=True)
    temp_html = NamedTemporaryFile(suffix='.html')
    with open(temp_html.name, 'w') as f:
        f.write(html)
        
    temp_img = NamedTemporaryFile(suffix='.png')
    with open(temp_img.name, 'wb') as f:
        chrome = r"/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome"
        args = f' --headless --window-size=1000,900 --hide-scrollbars --screenshot={temp_img.name} {temp_html.name}'
        run(chrome + args, shell=True)
    
    pil_data = Image.open(temp_img.name)
    image_arr = np.array(pil_data)
    column_avg = image_arr.mean(axis=2).mean(axis=0)[::-1]
    row_avg = image_arr.mean(axis=2).mean(1)
    last_col = image_arr.shape[1] - np.where(column_avg != 255)[0][0] + 10
    first_row = max(0, np.where(row_avg != 255)[0][0] - 20)
    last_row = image_arr.shape[0] - np.where(row_avg[::-1] != 255)[0][0] + 10
    image_arr = image_arr[first_row:last_row, :]
    img = Image.fromarray(image_arr)
    buffered = io.BytesIO()
    img.save(buffered, format="png", quality=95)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

pd.DataFrame._repr_png_ = f
