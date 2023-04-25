import base64
import io
import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageOps

from .pd_html import styler2html

_logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE = 65535 


def get_system():
    system = platform.system().lower()
    if system in ["darwin", "linux", "windows"]:
        return system
    else:
        raise OSError(f"Unsupported OS - {system}")


def get_chrome_path(chrome_path=None):
    system = get_system()
    if chrome_path:
        return chrome_path

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
        commands = [
            "google-chrome",
            "chrome",
            "chromium",
            "chromium-browser",
            "brave-browser",
        ]
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
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\brave.exe",
        ]
        for loc in locs:
            handle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, loc)
            num_values = winreg.QueryInfoKey(handle)[1]
            if num_values > 0:
                return winreg.EnumValue(handle, 0)[1]
        raise OSError("Cannot find chrome.exe on your windows machine")


class Screenshot:
    def __init__(
        self,
        center_df=True,
        max_rows=None,
        max_cols=None,
        chrome_path=None,
        fontsize=18,
        encode_base64=True,
        limit_crop=True,
        device_scale_factor=1,
    ):
        self.center_df = center_df
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.chrome_path = get_chrome_path(chrome_path)
        self.fontsize = fontsize
        self.encode_base64 = encode_base64
        self.limit_crop = limit_crop
        self.device_scale_factor = device_scale_factor

    def get_css(self):
        mod_dir = Path(__file__).resolve().parent
        css_file = mod_dir / "static" / "style.css"
        with open(css_file) as f:
            css = "<style>" + f.read() + "</style>"
        justify = "center" if self.center_df else "left"
        css = css.format(fontsize=self.fontsize, justify=justify)
        return css

    def take_screenshot(self, ss_width=1400, ss_height=900):
        html_css = self.get_css() + self.html
        with TemporaryDirectory() as temp_dir:
            temp_html = Path(temp_dir) / "temp.html"
            temp_img = Path(temp_dir) / "temp.png"
            with open(temp_html, "w", encoding="utf-8") as f:
                f.write(html_css)

            args = [
                "--enable-logging",
                "--disable-gpu",
                "--headless",
                # "--no-sandbox",
                f"--crash-dumps-dir={temp_dir}",
                f"--force-device-scale-factor={self.device_scale_factor}",
            ]
            # root user needs no-sandbox
            if platform.system().lower() != "windows" and os.geteuid() == 0:
                args.append("--no-sandbox")

            if ss_width and ss_height:
                args.append(f"--window-size={ss_width},{ss_height}")

            args += [
                "--hide-scrollbars",
                f"--screenshot={str(temp_img)}",
                str(temp_html),
            ]

            self.generate_image_from_html(args)
            with open(temp_img, "rb") as f:
                bio = io.BytesIO(f.read())
            im = Image.open(bio)
        return self.possibly_enlarge(im, ss_width, ss_height)

    def generate_image_from_html(self, args):
        # print(self.chrome_path)
        subprocess.run(executable=self.chrome_path, args=args, capture_output=True, check=True)

    def possibly_enlarge(self, img, ss_width, ss_height):
        enlarge = False
        im_ndarray = np.array(img)
        img2d = im_ndarray.mean(axis=2) == 255

        all_white_vert = img2d.all(axis=0)
        # must be all white for 30 pixels in a row to trigger stop
        if all_white_vert[-30:].sum() != 30:
            ss_width = int(ss_width * 1.5)
            enlarge = True

        all_white_horiz = img2d.all(axis=1)
        if all_white_horiz[-30:].sum() != 30:
            ss_height = int(ss_height * 1.5)
            enlarge = True

        if enlarge:
            if ss_height < MAX_IMAGE_SIZE and ss_width < MAX_IMAGE_SIZE:
                return self.take_screenshot(ss_width, ss_height)
            else:
                _logger.warning(
                    f"""Unable to enlarge image with Chrome, it is a known bug with version 111 and 112
                    You could try to install an individual Chrome dev version and set chrome_path to it
                    or try 'df.dfi.export('df.png', table_conversion="selenium")'"""
                )

        return self.crop(img)

    def crop(self, im):
        # remove black
        imrgb = im.convert("RGB")
        imageBox = imrgb.getbbox()
        im = im.crop(imageBox)

        # remove alpha channel
        imrgb = im.convert("RGB")
        # invert image (so that white is 0)
        invert_im = ImageOps.invert(imrgb)
        imageBox = invert_im.getbbox()
        cropped = im.crop(imageBox)
        return cropped

    def finalize_image(self, img):
        buffer = io.BytesIO()
        img.save(buffer, format="png")
        img_str = buffer.getvalue()
        if self.encode_base64:
            img_str = base64.b64encode(img_str).decode()
        return img_str

    def run(self, html):
        self.html = html
        img = self.take_screenshot()
        img_str = self.finalize_image(img)
        return img_str

    def repr_png_wrapper(self):
        from pandas.io.formats.style import Styler

        ss = self

        def _repr_png_(self):
            if isinstance(self, Styler):
                html = styler2html(self)
            else:
                html = self.to_html(max_rows=ss.max_rows, max_cols=ss.max_cols, notebook=True)
            return ss.run(html)

        return _repr_png_


def make_repr_png(center_df=True, max_rows=30, max_cols=10, chrome_path=None):
    """
    Used to create a _repr_png_ method for DataFrames and Styler objects
    so that nbconvert can use it to create images directly when
    executing the notebook before conversion to pdf/markdown.

    Parameters
    ----------
    center_df : bool, default True
        Choose whether to center the DataFrames or not in the image. By
        default, this is True, though in Jupyter Notebooks, they are
        left-aligned. Use False to make left-aligned.

    max_rows : int, default 30
        Maximum number of rows to output from DataFrame. This is forwarded to
        the `to_html` DataFrame method.

    max_cols : int, default 10
        Maximum number of columns to output from DataFrame. This is forwarded
        to the `to_html` DataFrame method.

    chrome_path : str, default None
        Path to your machine's chrome executable. When `None`, it is
        automatically found. Use this when chrome is not automatically found.
    """
    ss = Screenshot(center_df, max_rows, max_cols, chrome_path)
    return ss.repr_png_wrapper()
