import io
import os
import platform
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from dataframe_image.converter.browser.base import BrowserConverter
from dataframe_image.logger import logger


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
                    logger.info(f"Found Chrome executable at {chrome_path}")
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
            try:
                handle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, loc)
                num_values = winreg.QueryInfoKey(handle)[1]
            except FileNotFoundError:
                num_values = 0
            if num_values > 0:
                return winreg.EnumValue(handle, 0)[1]
        raise OSError("Cannot find chrome.exe on your windows machine")


class ChromeConverter(BrowserConverter):
    def __init__(
        self,
        center_df: bool = True,
        max_rows: int = None,
        max_cols: int = None,
        chrome_path: str = None,
        fontsize: int = 18,
        encode_base64: bool = True,
        crop_top: bool = True,
        device_scale_factor: int = 1,
        use_mathjax: bool = False,
    ):
        super().__init__(
            center_df,
            max_rows,
            max_cols,
            chrome_path,
            fontsize,
            encode_base64,
            crop_top,
            device_scale_factor,
            use_mathjax,
        )
        self.chrome_path = get_chrome_path(chrome_path)

    def screenshot(self, html, ss_width=1400, ss_height=900) -> Image:
        html_css = self.get_css() + html
        # create temp dir under current user home dir
        # snap version Chrome only allow to access files under home dir
        dfi_cache_dir = Path.home() / ".dataframe_image"
        dfi_cache_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=dfi_cache_dir) as temp_dir:
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
            if (
                os.environ.get("NO_SANDBOX", False)
                or platform.system().lower() != "windows"
                and os.geteuid() == 0
            ):
                args.append("--no-sandbox")

            if ss_width and ss_height:
                args.append(f"--window-size={ss_width},{ss_height}")

            args += [
                "--hide-scrollbars",
                f"--screenshot={str(temp_img)}",
                str(temp_html),
            ]

            subprocess.run(
                executable=self.chrome_path, args=args, capture_output=True, check=True
            )
            with open(temp_img, "rb") as f:
                bio = io.BytesIO(f.read())
            im = Image.open(bio)
            enlarge, ss_width, ss_height = self.should_enlarge(im, ss_width, ss_height)
            if enlarge:
                if ss_height < self.MAX_IMAGE_SIZE and ss_width < self.MAX_IMAGE_SIZE:
                    return self.screenshot(html, ss_width, ss_height)
                else:
                    logger.warning(
                        """Unable to enlarge image with Chrome, it is a known bug with version 111 and 112
                        You could try to install an individual Chrome dev version and set `chrome_path` to it
                        or try 'df.dfi.export('df.png', table_conversion="playwright")'"""
                    )
            return im


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
    ss = ChromeConverter(center_df, max_rows, max_cols, chrome_path)
    return ss.repr_png_wrapper()
