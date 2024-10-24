import io
from pathlib import Path

from PIL import Image

from dataframe_image.logger import logger

from .base import BrowserConverter


class Html2ImageConverter(BrowserConverter):
    def screenshot(
        self, html: str, ss_width: int = 1920, ss_height: int = 1080
    ) -> Image:
        from html2image import Html2Image

        css = self.get_css()
        # use folder under home directory to avoid permission issues
        # snap version Chrome can only access files under home dir
        wd = Path.home() / ".cache" / "html2image"
        wd.mkdir(parents=True, exist_ok=True)
        hti = Html2Image(
            browser_executable=self.chrome_path, output_path=wd, temp_path=str(wd)
        )
        hti.browser.flags = [
            f"--force-device-scale-factor={self.device_scale_factor}",
            "--disable-gpu",
            "--hide-scrollbars",
        ]
        outpaths = hti.screenshot(
            html_str=html, css_str=css, size=(ss_width, ss_height)
        )
        temp_img = outpaths[0]
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
                    You could try to install an individual Chrome dev version and set chrome_path to it
                    or try 'df.dfi.export('df.png', table_conversion="selenium")'"""
                )
        return im
