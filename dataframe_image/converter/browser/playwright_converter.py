import math
from io import BytesIO

from PIL import Image

from dataframe_image.logger import logger

from .base import BrowserConverter

MATHJAX_TIMEOUT = 10000
SCREENSHOT_TIMEOUT = 1000
MAX_TILE_SIDE = 4000


class _PlayWrightBase(BrowserConverter):
    channels = ["chrome", "msedge", "chromium", "firefox", None]
    _TABLE_RECT_SCRIPT = """(el) => {
        const r = el.getBoundingClientRect();
        return {
            x: r.left + window.scrollX,
            y: r.top + window.scrollY,
            width: r.width,
            height: r.height
        };
    }"""

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

    @staticmethod
    def _no_browser_error_message():
        return (
            "Could not find any chromium based browser. Make sure you have a "
            "chromium browser installed. Or install it by `playwright install chromium`."
        )

    @staticmethod
    def _clip_from_rect(rect):
        clip_x = max(0, int(math.floor(rect["x"])))
        clip_y = max(0, int(math.floor(rect["y"])))
        clip_width = max(1, int(math.ceil(rect["width"])))
        clip_height = max(1, int(math.ceil(rect["height"])))
        if clip_width > MAX_TILE_SIDE:
            raise ValueError(
                "DataFrame is too wide for Playwright fallback screenshot tiling. "
                "Try a lower dpi or reduce dataframe width."
            )
        return clip_x, clip_y, clip_width, clip_height

    @staticmethod
    def _image_from_bytes(image_bytes):
        return Image.open(BytesIO(image_bytes))

    @staticmethod
    def _viewport_from_bbox(bbox):
        return {
            "width": math.ceil(bbox["width"]) + 20,
            "height": math.ceil(bbox["height"]) + 20,
        }

    def _require_bbox(self, bbox, error_cls):
        if bbox is None:
            raise error_cls("Could not locate dataframe table in rendered HTML.")
        return bbox

    def _stitch_tiles(self, clip_width, clip_height, take_tile):
        stitched = Image.new("RGBA", (clip_width, clip_height))
        offset_y = 0
        while offset_y < clip_height:
            tile_height = min(MAX_TILE_SIDE, clip_height - offset_y)
            tile_bytes = take_tile(offset_y, tile_height)
            tile = Image.open(BytesIO(tile_bytes)).convert("RGBA")
            stitched.paste(tile, (0, offset_y))
            offset_y += tile_height

        output = BytesIO()
        stitched.save(output, format="PNG")
        return output.getvalue()

class PlayWrightConverter(_PlayWrightBase):

    def _launch_browser(self, playwright, error_cls):
        for channel in self.channels:
            try:
                return playwright.chromium.launch(
                    channel=channel,
                    args=["--disable-web-security"],
                    executable_path=self.chrome_path,
                )
            except error_cls:
                pass
        raise error_cls(self._no_browser_error_message())

    def _wait_for_mathjax(self, page, error_cls):
        if not self.use_mathjax:
            return
        mj = page.locator("mjx-container math")
        try:
            mj.wait_for(timeout=MATHJAX_TIMEOUT)
        except error_cls:
            logger.warning(
                "MathJax did not render in time. Formula in dataframe may not be rendered correctly."
            )
        page.wait_for_timeout(200)

    def _tiled_screenshot(self, page, locator):
        rect = locator.evaluate(self._TABLE_RECT_SCRIPT)
        clip_x, clip_y, clip_width, clip_height = self._clip_from_rect(rect)

        def _take_tile(offset_y, tile_height):
            return page.screenshot(
                clip={
                    "x": clip_x,
                    "y": clip_y + offset_y,
                    "width": clip_width,
                    "height": tile_height,
                },
                timeout=SCREENSHOT_TIMEOUT,
            )

        return self._stitch_tiles(clip_width, clip_height, _take_tile)

    def screenshot(self, html):
        try:
            from playwright.sync_api import Error, sync_playwright
        except ImportError as ex:
            raise ImportError(
                "Playwright is not installed. Install it with 'pip install playwright' and make sure you have a chromium browser installed."
            ) from ex

        with sync_playwright() as p:
            browser = self._launch_browser(p, Error)

            context = browser.new_context(
                device_scale_factor=self.device_scale_factor, bypass_csp=True
            )
            page = context.new_page()
            page.set_content(self.build_valid_html(html))
            locator = page.locator("#dfi_table table")
            bbox = self._require_bbox(locator.bounding_box(), Error)
            page.set_viewport_size(self._viewport_from_bbox(bbox))
            self._wait_for_mathjax(page, Error)
            try:
                screenshot_bytes = locator.screenshot()
            except Error as ex:
                logger.warning(f"Locator screenshot failed. Taking full page screenshot instead. Error: {ex}")
                try:
                    screenshot_bytes = page.screenshot(timeout=SCREENSHOT_TIMEOUT)
                except Error as page_ex:
                    logger.warning(
                        "Page screenshot failed. Falling back to tiled screenshots. "
                        f"Error: {page_ex}"
                    )
                    screenshot_bytes = self._tiled_screenshot(page, locator)
        return self._image_from_bytes(screenshot_bytes)


class AsyncPlayWrightConverter(_PlayWrightBase):

    async def _launch_browser(self, playwright, error_cls):
        for channel in self.channels:
            try:
                return await playwright.chromium.launch(
                    channel=channel,
                    args=["--disable-web-security"],
                    executable_path=self.chrome_path,
                )
            except error_cls:
                pass
        raise error_cls(self._no_browser_error_message())

    async def _wait_for_mathjax(self, page, error_cls):
        if not self.use_mathjax:
            return
        mj = page.locator("mjx-container math")
        try:
            await mj.wait_for(timeout=MATHJAX_TIMEOUT)
        except error_cls:
            logger.warning(
                "MathJax did not render in time. Formula in dataframe may not be rendered correctly."
            )
        await page.wait_for_timeout(200)

    async def _tiled_screenshot(self, page, locator):
        rect = await locator.evaluate(self._TABLE_RECT_SCRIPT)
        clip_x, clip_y, clip_width, clip_height = self._clip_from_rect(rect)

        stitched = Image.new("RGBA", (clip_width, clip_height))
        offset_y = 0
        while offset_y < clip_height:
            tile_height = min(MAX_TILE_SIDE, clip_height - offset_y)
            tile_bytes = await page.screenshot(
                clip={
                    "x": clip_x,
                    "y": clip_y + offset_y,
                    "width": clip_width,
                    "height": tile_height,
                },
                timeout=SCREENSHOT_TIMEOUT,
            )
            tile = Image.open(BytesIO(tile_bytes)).convert("RGBA")
            stitched.paste(tile, (0, offset_y))
            offset_y += tile_height

        output = BytesIO()
        stitched.save(output, format="PNG")
        return output.getvalue()

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
            browser = await self._launch_browser(p, Error)

            context = await browser.new_context(
                device_scale_factor=self.device_scale_factor, bypass_csp=True
            )
            page = await context.new_page()
            await page.set_content(self.build_valid_html(html))
            locator = page.locator("#dfi_table table")
            bbox = self._require_bbox(await locator.bounding_box(), Error)
            await page.set_viewport_size(self._viewport_from_bbox(bbox))
            await self._wait_for_mathjax(page, Error)
            try:
                screenshot_bytes = await locator.screenshot()
            except Error as ex:
                logger.warning(
                    "Locator screenshot failed. Taking full page screenshot instead. "
                    f"Error: {ex}"
                )
                try:
                    screenshot_bytes = await page.screenshot(timeout=SCREENSHOT_TIMEOUT)
                except Error as page_ex:
                    logger.warning(
                        "Page screenshot failed. Falling back to tiled screenshots. "
                        f"Error: {page_ex}"
                    )
                    screenshot_bytes = await self._tiled_screenshot(page, locator)
        return self._image_from_bytes(screenshot_bytes)
