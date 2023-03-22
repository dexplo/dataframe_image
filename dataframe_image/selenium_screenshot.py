import io
from tempfile import TemporaryDirectory

from pathlib import Path

from matplotlib import image as mimage
from ._screenshot import Screenshot


class SeleniumScreenshot(Screenshot):
    def __init__(
        self,
        center_df=True,
        max_rows=None,
        max_cols=None,
        fontsize=18,
        encode_base64=True,
        limit_crop=True,
        device_scale_factor=1,
    ):
        self.center_df = center_df
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.css = self.get_css(fontsize)
        self.encode_base64 = encode_base64
        self.limit_crop = limit_crop
        self.device_scale_factor = device_scale_factor

    def take_screenshot(self):
        try:
            import selenium.webdriver
            import selenium.common

            options = selenium.webdriver.FirefoxOptions()
            options.add_argument("--headless")

            profile = selenium.webdriver.FirefoxProfile()
            profile.set_preference("layout.css.devPixelsPerPx", str(self.device_scale_factor))
            profile.set_preference("webdriver.log.file", "/tmp/firefox_console")
            options.profile = profile
        except ImportError:
            raise ImportError(
                "Selenium is not installed. Install it with 'pip install selenium' and make sure you have a firefox webdriver installed."
            )

        temp_dir = TemporaryDirectory()
        temp_html = Path(temp_dir.name) / "temp.html"
        temp_img = Path(temp_dir.name) / "temp.png"
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(self.html)

        with selenium.webdriver.Firefox(options=options) as driver:
            driver.get(f"file://{str(temp_html)}")  # selenium will do the rest

            required_width = driver.execute_script("return document.body.parentNode.scrollWidth")
            required_height = driver.execute_script("return document.body.parentNode.scrollHeight")
            driver.set_window_size(required_width + 150, required_height + 90)
            driver.save_screenshot(str(temp_img))

        # subprocess.run(executable=self.chrome_path, args=args)

        with open(temp_img, "rb") as f:
            img_bytes = f.read()

        buffer = io.BytesIO(img_bytes)
        img = mimage.imread(buffer)

        # sometimes the image bottom has a black line at device_scale_factor > 6, so we crop it
        img2d = img.mean(axis=2) == 0
        all_black_vert = img2d.all(axis=0)
        all_black_horiz = img2d.all(axis=1)
        img = self.crop(img, all_black_vert, all_black_horiz)

        # calculate the crop
        img2d = img.mean(axis=2) == 1
        all_white_vert = img2d.all(axis=0)
        all_white_horiz = img2d.all(axis=1)

        return self.crop(img, all_white_vert, all_white_horiz)
