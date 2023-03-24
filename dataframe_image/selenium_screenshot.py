import io
from tempfile import TemporaryDirectory

from pathlib import Path

from PIL import Image
from ._screenshot import Screenshot
from selenium.webdriver.firefox.service import Service


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
        self.fontsize = fontsize
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

            options.profile = profile
            
            service = Service(log_path="/tmp/firefox_console")
        except ImportError:
            raise ImportError(
                "Selenium is not installed. Install it with 'pip install selenium' and make sure you have a firefox webdriver installed."
            )

        temp_dir = TemporaryDirectory()
        temp_html = Path(temp_dir.name) / "temp.html"
        temp_img = Path(temp_dir.name) / "temp.png"
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(self.get_css() + self.html)

        with selenium.webdriver.Firefox(options=options, service=service) as driver:
            driver.get(f"file://{str(temp_html)}")  # selenium will do the rest

            required_width = driver.execute_script("return document.body.parentNode.scrollWidth")
            required_height = driver.execute_script("return document.body.parentNode.scrollHeight")
            driver.set_window_size(required_width + 150, required_height + 90)
            driver.save_screenshot(str(temp_img))

        # subprocess.run(executable=self.chrome_path, args=args)

        img = Image.open(temp_img)
        return self.crop(img)
