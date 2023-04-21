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

import aiohttp
from nbconvert.exporters import Exporter, HTMLExporter

from ._screenshot import get_chrome_path


async def handler(ws, data, key=None):
    await ws.send_json(data)
    async for msg in ws:
        msg_json = msg.json()
        if "result" in msg_json:
            result = msg_json["result"].get(key)
            break
    return result


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
                    raise Exception(
                        "Chrome process has died with code: %s" % p.returncode
                    )
                logging.warning(ex)
                await asyncio.sleep(1)
            if connected:
                break
        if not connected:
            p.kill()
            raise Exception("Could not connect to chrome server")

        async with session.ws_connect(
            page_url, receive_timeout=3, max_msg_size=0
        ) as ws:
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
            await asyncio.sleep(1)
            params = {"displayHeaderFooter": False, "printBackground": True}
            data = {"id": 4, "method": "Page.printToPDF", "params": params}
            pdf_data = await handler(ws, data, "data")
            pdf_data = base64.b64decode(pdf_data)
            return pdf_data


def launch_chrome():
    chrome_path = get_chrome_path()
    temp_dir = TemporaryDirectory()
    args = [
        chrome_path,
        "--headless",
        "--enable-logging",
        "--disable-gpu",
        # "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--remote-debugging-port=9222",
        f"--crash-dumps-dir={temp_dir.name}",
    ]
    if platform.system().lower() != "windows" and os.geteuid() == 0:
        args.append("--no-sandbox")
    p = Popen(args=args)
    return p


def get_html_data(nb, resources, **kw):
    he = HTMLExporter()
    html_data, resources = he.from_notebook_node(nb, resources, **kw)
    html_data = html_data.replace("@media print", "@media xxprintxx")
    return html_data


def get_pdf_data(file_name, p):
    try:
        from asyncio import run
    except ImportError:
        from ._my_asyncio import run

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future = executor.submit(run, main(file_name, p))
    return future.result()


class BrowserExporter(Exporter):
    def _file_extension_default(self):
        return ".pdf"

    def from_notebook_node(self, nb, resources=None, **kw):
        resources["output_extension"] = ".pdf"
        nb_home = resources["metadata"]["path"]

        p = launch_chrome()
        html_data = get_html_data(nb, resources, **kw)
        _, tf_name = mkstemp(dir=nb_home, suffix=".html")
        with open(tf_name, "w", encoding="utf-8") as f:
            f.write(html_data)
        tf_path = Path(tf_name)
        full_file_name = "file://" + urllib.parse.quote(tf_name)
        pdf_data = get_pdf_data(full_file_name, p)
        import os

        os.remove(tf_path)
        p.kill()
        return pdf_data, resources
