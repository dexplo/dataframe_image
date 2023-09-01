import base64
import io
import logging
import subprocess
from abc import ABC
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageOps

from dataframe_image.pd_html import styler2html

_logger = logging.getLogger(__name__)


class BrowserConverter(ABC):
    MAX_IMAGE_SIZE = 65535

    def __init__(
        self,
        center_df: bool = True,
        max_rows: int = None,
        max_cols: int = None,
        chrome_path: str = None,
        fontsize: int = 18,
        encode_base64: bool = True,
        limit_crop: bool = True,
        device_scale_factor: int = 1,
        use_mathjax: bool = False,
    ):
        """
        Initialize the Html2ImageConverter class.

        Args:
            center_df (bool): Whether to center the dataframe. Default is True.
            max_rows (int): Maximum number of rows. Default is None.
            max_cols (int): Maximum number of columns. Default is None.
            chrome_path (str): Path to the Chrome executable. Default is None.
            fontsize (int): Font size. Default is 18.
            encode_base64 (bool): Whether to encode the image in base64. Default is True.
            limit_crop (bool): Whether to limit the crop. Default is True.
            device_scale_factor (int): Device scale factor. Default is 1.
            use_mathjax (bool): Whether to use MathJax for rendering. Default is False.
        """
        self.center_df = center_df
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.chrome_path = chrome_path
        self.fontsize = fontsize
        self.encode_base64 = encode_base64
        self.limit_crop = limit_crop
        self.device_scale_factor = device_scale_factor
        self.use_mathjax = use_mathjax

    def get_css(self) -> str:
        """
        Get the CSS for the HTML.

        Returns:
            str: The CSS string.
        """
        mod_dir = Path(__file__).resolve().parent
        css_file = mod_dir / "static" / "style.css"
        with open(css_file) as f:
            css = "<style>" + f.read() + "</style>"
        justify = "center" if self.center_df else "left"
        css = css.format(fontsize=self.fontsize, justify=justify)
        if self.use_mathjax:
            script = """<script>
            MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\(', '\\)']]
            },
            svg: {
                fontCache: 'global'
            }
            };
            </script>
            <script type="text/javascript" id="MathJax-script" async
            src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
            </script>
            <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script> 
            <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>"""
            css += script
        return css

    def should_enlarge(self, img: Image, ss_width: int, ss_height: int) -> tuple:
        """
        Check if the image should be enlarged.

        Args:
            img (Image): The image to check.
            ss_width (int): The screenshot width.
            ss_height (int): The screenshot height.

        Returns:
            tuple: A tuple containing a boolean indicating whether to enlarge the image, and the new width and height.
        """
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

        return enlarge, ss_width, ss_height

    def screenshot(
        self, html: str, ss_width: int = 1920, ss_height: int = 1080
    ) -> Image:
        """
        Take a screenshot of the HTML.

        Args:
            html (str): The HTML to screenshot.
            ss_width (int): The screenshot width. Default is 1920.
            ss_height (int): The screenshot height. Default is 1080.

        Returns:
            Image: The screenshot image.
        """
        raise NotImplementedError

    def crop(self, im: Image) -> Image:
        """
        Crop the image.

        Args:
            im (Image): The image to crop.

        Returns:
            Image: The cropped image.
        """
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

    def run(self, html: str) -> bytes:
        """
        Run the converter on the HTML.

        Args:
            html (str): The HTML to convert.

        Returns:
            bytes: The converted image bytes.
        """
        im = self.screenshot(html)
        temp_img = self.crop(im)
        image_bytes = self.finalize_image(temp_img)
        return image_bytes

    def finalize_image(self, img: Image) -> bytes:
        """
        Finalize the image.

        Args:
            img (Image): The image to finalize.

        Returns:
            bytes: The finalized image bytes.
        """
        buffer = io.BytesIO()
        img.save(buffer, format="png")
        img_str = buffer.getvalue()
        if self.encode_base64:
            img_str = base64.b64encode(img_str).decode()
        return img_str

    def repr_png_wrapper(self):
        from pandas.io.formats.style import Styler

        ss = self

        def _repr_png_(self):
            if isinstance(self, Styler):
                html = styler2html(self)
            else:
                html = self.to_html(
                    max_rows=ss.max_rows, max_cols=ss.max_cols, notebook=True
                )
            return ss.run(html)

        return _repr_png_
