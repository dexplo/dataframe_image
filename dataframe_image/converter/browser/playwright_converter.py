from io import BytesIO

from PIL import Image

from dataframe_image.logger import logger

from .base import BrowserConverter


class PlayWrightConverter(BrowserConverter):
    def screenshot(self, html):
        try:
            from playwright.sync_api import Error, sync_playwright
        except ImportError as ex:
            raise ImportError(
                "Playwright is not installed. Install it with 'pip install playwright' and make sure you have a chromium browser installed."
            ) from ex
        with sync_playwright() as p:
            channels = ["chrome", "msedge", None]
            for c in channels:
                try:
                    browser = p.chromium.launch(channel=c, args=["--disable-web-security"])
                    break
                except Error:
                    pass
            else:
                raise Error(
                    "Could not find any chromium based browser. Make sure you have a chromium browser installed."
                    "Or install it by `playwright install chromium`"
                )

            context = browser.new_context(device_scale_factor=self.device_scale_factor, bypass_csp=True)
            page = context.new_page()
            page.set_content(self.get_css() + html)
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
            screenshot_bytes = page.screenshot(full_page=True)
        im = Image.open(BytesIO(screenshot_bytes))
        return im


class AsyncPlayWrightConverter(BrowserConverter):
    
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
            channels = ["chromium", "chrome", "msedge", None]
            for c in channels:
                try:
                    browser = await p.chromium.launch(
                        channel=c, args=["--disable-web-security"]
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
            await page.set_content(self.get_css() + html)
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
            screenshot_bytes = await page.screenshot(full_page=True)
        im = Image.open(BytesIO(screenshot_bytes))
        return im