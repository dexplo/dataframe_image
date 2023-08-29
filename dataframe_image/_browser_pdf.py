import asyncio
import base64
import concurrent.futures
import logging
import os
import platform
import urllib.parse
from pathlib import Path
from subprocess import Popen
from tempfile import TemporaryDirectory, mkstemp
import ChromeController

import aiohttp
from nbconvert import TemplateExporter
from nbconvert.exporters import Exporter, HTMLExporter

from ._screenshot import get_chrome_path


async def handler(ws, data, key=None):
    await ws.send_json(data)
    async for msg in ws:
        msg_json = msg.json()
        if "result" in msg_json:
            result = msg_json["result"].get(key)
            break
    else:
        raise Exception("{data} failed")
    return result

# deprecated
async def main(file_name, p):
    async with aiohttp.ClientSession() as session:
        connected = False
        await asyncio.sleep(1)
        for _ in range(20):
            try:
                resp = await session.get("http://localhost:9222/json")
                data = await resp.json()
                page_url = data[0]["webSocketDebuggerUrl"]
                connected = True
            except Exception as ex:
                if p.returncode is not None:
                    raise Exception("Chrome process has died with code: %s" % p.returncode)
                logging.warning(ex)
                await asyncio.sleep(1)
            if connected:
                break
        if not connected:
            p.kill()
            raise Exception("Could not connect to chrome server")

        async with session.ws_connect(page_url, receive_timeout=3, max_msg_size=0) as ws:
            # first - navigate to html page
            params = {"url": file_name}
            data = {"id": 1, "method": "Page.navigate", "params": params}
            frameId = await handler(ws, data, "frameId")

            # second - enable page
            # await asyncio.sleep(1)
            data = {"id": 2, "method": "Page.enable"}
            await handler(ws, data)

            # third - get html
            params = {"frameId": frameId, "url": file_name}
            data = {"id": 3, "method": "Page.getResourceContent", "params": params}
            await handler(ws, data, "content")

            # fourth - get pdf
            for i in range(10):
                await asyncio.sleep(1)
                params = {"displayHeaderFooter": False, "printBackground": True}
                data = {"id": 4, "method": "Page.printToPDF", "params": params}
                pdf_data = await handler(ws, data, "data")
                pdf_data = base64.b64decode(pdf_data)
                if len(pdf_data) > 1000:
                    break
            else:
                raise Exception("Could not get pdf data")
            return pdf_data


def get_launch_args():
    # temp_dir = TemporaryDirectory()
    temp_dir_name = os.path.abspath(".")
    args = [
        "--headless",
        "--enable-logging",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--remote-allow-origins=*",
        f"--crash-dumps-dir={temp_dir_name}",
        "about:blank",
    ]
    if (
        os.environ.get("NO_SANDBOX", False)
        or platform.system().lower() != "windows"
        and os.geteuid() == 0
    ):
        args.append("--no-sandbox")
    return args

# deprecated
def launch_chrome():
    chrome_path = get_chrome_path()
    args = [chrome_path] + get_launch_args() + ["--remote-debugging-port=9222"]
    p = Popen(args=args)
    return p



# deprecated
def get_pdf_data(file_name):
    p = launch_chrome()
    try:
        from asyncio import run
    except ImportError:
        from ._my_asyncio import run

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future = executor.submit(run, main(file_name, p))
        data =  future.result()
    p.kill()
    return data


def get_pdf_data_chromecontroller(file_name):
    additional_options = get_launch_args()
    # ChromeContext will shlex.split binary, so add quote to it
    with ChromeController.ChromeContext(
        binary=f'"{get_chrome_path()}"', additional_options=additional_options
    ) as cr:
        # Do a blocking navigate to a URL, and get the page content as served by the remote
        # server, with no modification by local javascript (if applicable)
        raw_source = cr.blocking_navigate_and_get_source(file_name)
        # Since the page is now rendered by the blocking navigate, we can
        # get the page source after any javascript has modified it.
        rendered_source = cr.get_rendered_page_source()
        # # Or take a screenshot
        # # The screenshot is the size of the remote browser's configured viewport,
        # # which by default is set to 1024 * 1366. This size can be changed via the
        # # Emulation_setVisibleSize(width, height) function if needed.
        # png_bytestring = cr.take_screeshot()

        response = cr.Page_printToPDF(**{"displayHeaderFooter": False, "printBackground": True})
        data = response["result"]["data"]
        pdf_data = base64.b64decode(data)
        return pdf_data


class BrowserExporter(HTMLExporter):
    def _file_extension_default(self):
        return ".pdf"
    
    def _template_extension_default(self):
        return ".html.j2"

    def from_notebook_node(self, nb, resources=None, **kw):
        resources["output_extension"] = ".pdf"
        nb_home = resources["metadata"]["path"]

        html_data, resources = super().from_notebook_node(nb, resources, **kw)
        html_data = html_data.replace("@media print", "@media xxprintxx")
        fd, tf_name = mkstemp(dir=nb_home, suffix=".html")
        with open(fd, "w", encoding="utf-8") as f:
            f.write(html_data)
        tf_path = Path(tf_name)
        file_uri = tf_path.as_uri()
        # pdf_data = get_pdf_data_chromecontroller(file_uri)
        pdf_data = get_pdf_data(file_uri)
        os.remove(tf_path)
        return pdf_data, resources
