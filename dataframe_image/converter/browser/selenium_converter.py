from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from .base import BrowserConverter


class SeleniumConverter(BrowserConverter):
    def screenshot(self, html: str) -> Image:
        # by default Firefox will cleanup it's profile directory after closing
        # so we need to set ignore_cleanup_errors=True

        temp_dir_obj = TemporaryDirectory(prefix="dataframe_image_")
        temp_dir = temp_dir_obj.name
        try:
            import selenium.common
            import selenium.webdriver
            from selenium.webdriver.firefox.service import Service

            options = selenium.webdriver.FirefoxOptions()
            options.add_argument("--headless")

            profile = selenium.webdriver.FirefoxProfile(temp_dir)
            profile.set_preference(
                "layout.css.devPixelsPerPx", str(self.device_scale_factor)
            )

            options.profile = profile

            service = Service(log_path=str(Path(temp_dir) / "geckodriver.log"))
        except ImportError:
            raise ImportError(
                "Selenium is not installed. Install it with 'pip install selenium' and make sure you have a firefox webdriver installed."
            )

        temp_html = Path(temp_dir) / "temp.html"
        temp_img = Path(temp_dir) / "temp.png"
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(self.get_css() + html)

        with selenium.webdriver.Firefox(options=options, service=service) as driver:
            driver.get(temp_html.as_uri())  # selenium will do the rest

            # get "#dfi_table table" width and height
            required_width = driver.execute_script(
                "return document.querySelector('#dfi_table table').scrollWidth"
            )
            required_height = driver.execute_script(
                "return document.querySelector('#dfi_table table').scrollHeight"
            )
            driver.set_window_size(required_width + 150, required_height + 90)
            driver.save_screenshot(str(temp_img))

            # temp_img will be deleted after context exit
            img = Image.open(temp_img)
        try:
            temp_dir_obj.cleanup()
        except OSError:
            pass
        return img
