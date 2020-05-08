import platform
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from subprocess import run
import base64
import io

import numpy as np
import pandas as pd
from PIL import Image


def get_system():
    system = platform.platform().lower()
    if system.startswith("darwin"):
        return "darwin"
    elif system.startswith("linux"):
        return "linux"
    elif system[:3] in ("win", "msy", "cyg"):
        return "windows"
    raise OSError(f"Unsupported OS - {system}")


def get_chrome_path():
    # help finding path - https://github.com/SeleniumHQ/selenium/wiki/ChromeDriver#requirements
    system = get_system()
    if system == "darwin":
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
        for path in paths:
            if Path(path).exists():
                return path
        raise OSError("Chrome executable not able to be found on your machine")
    elif system == "linux":
        paths = [
            None,
            "/usr/local/sbin",
            "/usr/local/bin",
            "/usr/sbin",
            "/usr/bin",
            "/sbin",
            "/bin",
            "/opt/google/chrome",
        ]
        commands = ["google-chrome", "chrome", "chromium", "chromium-browser", "brave-browser"]
        for path in paths:
            for cmd in commands:
                chrome_path = shutil.which(cmd, path=path)
                if chrome_path:
                    return chrome_path
        raise OSError("Chrome executable not able to be found on your machine")
    elif system == "windows":
        import winreg

        locs = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\brave.exe",
        ]
        for loc in locs:
            handle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, loc)
            num_values = winreg.QueryInfoKey(handle)[1]
            if num_values > 0:
                return winreg.EnumValue(handle, 0)[1]
        raise OSError("Cannot find chrome.exe on your windows machine")


def get_css():
    mod_dir = Path(__file__).resolve().parent
    css_file = mod_dir / "css" / "style.css"
    with open(css_file) as f:
        css = "<style>" + f.read() + "</style>"
    return css


def repr_png_maker(max_rows=30, max_cols=10, ss_width=1000, ss_height=900, 
                   resize=1, chrome_path=None):
    """
    Creates a function that can be assigned to `pd.DataFrame._repr_png_` 
    so that you can test out the appearances of the images in a notebook 
    before you convert.

    >>> import pandas as pd
    >>> from dataframe_image import repr_png_maker
    >>> pd.DataFrame._repr_png_ = repr_png_maker() # pass desired arguments
    >>> df = pd.DataFrame({'a': [1, 5, 6]})
    >>> from IPython.display import display_png
    >>> display_png(df)

    There is no need to use this function in the notebook that you want to 
    convert to pdf or markdown. Use `dataframe_image.convert` in a separate 
    script for that.

    Parameters
    ----------
    max_rows : int, default 30
        Maximum number of rows to output from DataFrame. This is forwarded to 
        the `to_html` DataFrame method.

    max_cols : int, default 10
        Maximum number of columns to output from DataFrame. This is forwarded 
        to the `to_html` DataFrame method.

    ss_width : int, default 1000
        Width of the screenshot. This may need to be increased for larger 
        monitors. If this value is too small, then smaller DataFrames will 
        appear larger. It's best to keep this value at least as large as the 
        width of the output section of a Jupyter Notebook.

    ss_height : int, default 900
        Height of the screen shot. The height of the image is automatically 
        cropped so that only the relevant parts of the DataFrame are shown.

    resize : int or float, default 1
        Relative resizing of image. Higher numbers produce smaller images. 
        The Pillow `Image.resize` method is used for this.

    chrome_path : str, default None
        Path to your machine's chrome executable. When `None`, it is 
        automatically found. Use this when chrome is not automatically found.
    """
    css = get_css()

    def f(self):
        nonlocal chrome_path
        html = css + self.to_html(max_cols=max_cols, max_rows=max_rows, notebook=True)
        temp_dir = TemporaryDirectory()
        temp_html = Path(temp_dir.name) / "temp.html"
        temp_img = Path(temp_dir.name) / "temp.png"
        open(temp_html, "w").write(html)
        open(temp_img, "wb")

        if chrome_path is None:
            chrome_path = get_chrome_path()

        args = [
            "--enable-logging",
            "--disable-gpu",
            "--headless",
            f"--window-size={ss_width},{ss_height}",
            "--hide-scrollbars",
            f"--screenshot={str(temp_img)}",
            str(temp_html),
        ]

        run(executable=chrome_path, args=args)

        pil_data = Image.open(str(temp_img))
        image_arr = np.array(pil_data)

        row_avg = image_arr.mean(axis=2).mean(1)
        first_row = max(0, np.where(row_avg != 255)[0][0] - 20)
        last_row = image_arr.shape[0] - np.where(row_avg[::-1] != 255)[0][0] + 10

        # not cropping width so that images appear the same size
        # column_avg = image_arr.mean(axis=2).mean(axis=0)[::-1]
        # last_col = image_arr.shape[1] - np.where(column_avg != 255)[0][0] + 10

        image_arr = image_arr[first_row:last_row, :]
        img = Image.fromarray(image_arr)
        if resize != 1:
            w, h = img.size
            w, h = int(w // resize), int(h // resize)
            img = img.resize((w, h), Image.ANTIALIAS)
        buffered = io.BytesIO()
        img.save(buffered, format="png", quality=95)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str

    return f
