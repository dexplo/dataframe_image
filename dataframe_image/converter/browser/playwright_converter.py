import math
from io import BytesIO

from PIL import Image

from dataframe_image.logger import logger

from .base import BrowserConverter


class PlayWrightConverter(BrowserConverter):
    def __init__(
        self,
        center_df=True,
        max_rows=None,
        max_cols=None,
        chrome_path=None,
        fontsize=18,
        encode_base64=True,
        crop_top=True,
        device_scale_factor=1,
        use_mathjax=False,
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
        self.channels = ["chrome", "msedge", "chromium", "firefox", None]

    def screenshot(self, html):
        try:
            from playwright.sync_api import Error, sync_playwright
        except ImportError as ex:
            raise ImportError(
                "Playwright is not installed. Install it with 'pip install playwright' and make sure you have a chromium browser installed."
            ) from ex

        with sync_playwright() as p:
            for c in self.channels:
                try:
                    browser = p.chromium.launch(
                        channel=c,
                        args=["--disable-web-security"],
                        executable_path=self.chrome_path,
                    )
                    break
                except Error:
                    pass
            else:
                raise Error(
                    "Could not find any chromium based browser. Make sure you have a chromium browser installed."
                    "Or install it by `playwright install chromium`"
                )

            context = browser.new_context(
                device_scale_factor=self.device_scale_factor, bypass_csp=True
            )
            page = context.new_page()
            page.set_content(self.build_valid_html(html))
            # get height and width for #dfi_table
            locator = page.locator("#dfi_table table")
            bbox = locator.bounding_box()
            width = bbox["width"]
            height = bbox["height"]
            page.set_viewport_size(
                {"width": math.ceil(width) + 20, "height": math.ceil(height) + 20}
            )
            if self.use_mathjax:
                mj = page.locator("mjx-container math")
                try:
                    mj.wait_for(timeout=10000)
                except Error:
                    logger.warning(
                        "MathJax did not render in time. Formula in dataframe may not be rendered correctly."
                    )
                    pass
                page.wait_for_timeout(200)
            try:
                screenshot_bytes = locator.screenshot(timeout=1000)
            except Error:
                logger.warning("Locator screenshot timed out. Taking full page screenshot instead.")
                screenshot_bytes = page.screenshot(timeout=1000)
        im = Image.open(BytesIO(screenshot_bytes))
        return im


class AsyncPlayWrightConverter(BrowserConverter):
    def __init__(
        self,
        center_df=True,
        max_rows=None,
        max_cols=None,
        chrome_path=None,
        fontsize=18,
        encode_base64=True,
        crop_top=True,
        device_scale_factor=1,
        use_mathjax=False,
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
        self.channels = ["chrome", "msedge", "chromium", "firefox", None]

    async def run(self, html: str) -> bytes:
        im = await self.screenshot(html)
        temp_img = self.crop(im)
        image_bytes = self.finalize_image(temp_img)
        return image_bytes

    async def screenshot(self, html):
        try:
            from playwright.async_api import Error, async_playwright
        except ImportError as ex:
            raise ImportError(
                "Playwright is not installed. Install it with 'pip install playwright' "
                "and make sure you have a chromium browser installed."
            ) from ex
        async with async_playwright() as p:
            for c in self.channels:
                try:
                    browser = await p.chromium.launch(
                        channel=c,
                        args=["--disable-web-security"],
                        executable_path=self.chrome_path,
                    )
                    break
                except Error:
                    pass
            else:
                raise Error(
                    "Could not find any chromium based browser. Make sure you have a "
                    "chromium browser installed. Or install it by "
                    "`playwright install chromium`."
                )

            context = await browser.new_context(
                device_scale_factor=self.device_scale_factor, bypass_csp=True
            )
            page = await context.new_page()
            await page.set_content(self.build_valid_html(html))
            locator = page.locator("#dfi_table table")
            bbox = await locator.bounding_box()
            width = bbox["width"]
            height = bbox["height"]
            await page.set_viewport_size(
                {"width": math.ceil(width) + 20, "height": math.ceil(height) + 20}
            )
            if self.use_mathjax:
                mj = page.locator("mjx-container math")
                try:
                    mj.wait_for(timeout=10000)
                except Error:
                    logger.warning(
                        "MathJax did not render in time. Formula in dataframe may not "
                        "be rendered correctly."
                    )
                    pass
                page.wait_for_timeout(200)
            try:
                screenshot_bytes = await locator.screenshot(timeout=1000)
            except Error:
                logger.warning("Locator screenshot timed out. Taking full page screenshot instead.")
                screenshot_bytes = await page.screenshot(timeout=1000)
        im = Image.open(BytesIO(screenshot_bytes))
        return im
