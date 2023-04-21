import base64
from pathlib import Path


class Html2ImageConverter:
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
        self.chrome_path = chrome_path
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
    
    def run(self, html):
        from html2image import Html2Image
        css = self.get_css()
        # use folder under home directory to avoid permission issues
        wd = Path.home() / ".cache" / "html2image" 
        wd.mkdir(parents=True, exist_ok=True)
        hti = Html2Image(browser_executable=self.chrome_path, output_path=wd, temp_path=str(wd))
        hti.browser.flags = [f'--force-device-scale-factor={self.device_scale_factor}', '--disable-gpu', '--hide-scrollbars']
        outpaths = hti.screenshot(html_str=html, css_str=css, size=(9000, 900))
        image_bytes = self.finalize_image(outpaths[0])
        return image_bytes
    
    def finalize_image(self, image_path)->bytes:
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        if self.encode_base64:
            img_bytes = base64.b64encode(img_bytes)
        return img_bytes
