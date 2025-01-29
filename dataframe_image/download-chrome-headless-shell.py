"""This module handles downloading and extracting Chrome Headless builds for testing purposes.

It includes functionality to identify the current operating system, resolve download URLs based on
platform and release channel, and manage the extraction of downloaded archives.

Features:
    - Automatic identification of the operating system.
    - Downloading Chrome Headless builds from Google Chrome's public testing storage.
    - Extraction of ZIP archives to a specified directory, with proper permission settings.

Dependencies:
    - httpx: For HTTP requests.
    - zipfile: For handling ZIP archives.
    - platform: For system identification.

Usage:
    Run the module directly to download and extract the latest stable Chrome Headless build for the detected platform.

Example:
    python download-chrome-headless-shell.py
"""

import os
import aiohttp
from enum import Enum
import platform
import zipfile
import stat
import tempfile
import argparse

CHROME_LAST_KNOWN_GOOD_VERSION = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json"
CHROME_FOR_TESTING_PUBLIC_BASE_URL = "https://storage.googleapis.com/chrome-for-testing-public"


def ensure_directory_exists(directory: str):
    """Ensures that a directory exists, creating it if necessary.

    Args:
        directory (str): Path to the directory.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


class BrowserPlatform(Enum):
    """Enum representing supported browser platforms."""

    LINUX = "linux"
    MAC_ARM = "mac-arm"
    MAC = "mac"
    WIN32 = "win32"
    WIN64 = "win64"

    @staticmethod
    def identify_current_os() -> "BrowserPlatform":
        """Identifies the current operating system and returns the corresponding BrowserPlatform.

        Returns:
            BrowserPlatform: Enum value representing the detected OS.

        Raises:
            ValueError: If the operating system is unsupported.
        """
        system = platform.system()
        machine = platform.machine().lower()

        if system == "Linux":
            return BrowserPlatform.LINUX
        elif system == "Darwin":
            if machine == "arm64":
                return BrowserPlatform.MAC_ARM
            else:
                return BrowserPlatform.MAC
        elif system == "Windows":
            if "64" in machine:
                return BrowserPlatform.WIN64
            else:
                return BrowserPlatform.WIN32
        else:
            raise ValueError("Unsupported operating system")

    def get_folder(self) -> str:
        """Returns the folder name corresponding to the platform.

        Returns:
            str: Folder name for the platform.

        Raises:
            ValueError: If the platform is unsupported.
        """
        try:
            return {
                BrowserPlatform.LINUX: "linux64",
                BrowserPlatform.MAC_ARM: "mac-arm64",
                BrowserPlatform.MAC: "mac-x64",
                BrowserPlatform.WIN32: "win32",
                BrowserPlatform.WIN64: "win64",
            }.get(self)
        except KeyError:
            raise ValueError(f"Unsupported platform: {self}")


class ChromeReleaseChannel(Enum):
    """Enum representing Chrome release channels."""

    STABLE = "Stable"
    BETA = "Beta"
    DEV = "Dev"
    CANARY = "Canary"


def resolve_download_url(platform: BrowserPlatform, build_id: str) -> str:
    """Constructs the download URL for Chrome Headless based on platform and build ID.

    Args:
        platform (BrowserPlatform): The platform enum value.
        build_id (str): The build ID to download.

    Returns:
        str: Full URL for the Chrome Headless download.
    """
    return f"{CHROME_FOR_TESTING_PUBLIC_BASE_URL}/{'/'.join(resolve_download_path(platform, build_id))}"


def resolve_download_path(platform: BrowserPlatform, build_id: str) -> list[str]:
    """Resolves the download path components for Chrome Headless.

    Args:
        platform (BrowserPlatform): The platform enum value.
        build_id (str): The build ID to download.

    Returns:
        list[str]: List of path components for the download.
    """
    return [
        build_id,
        platform.get_folder(),
        f"chrome-headless-shell-{platform.get_folder()}.zip",
    ]


async def download_file(url: str, download_path: str):
    """Downloads a file from a URL and saves it to the specified path.

    Args:
        url (str): The URL to download from.
        download_path (str): Path to save the downloaded file.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            with open(download_path, "wb") as download_file:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    download_file.write(chunk)


def extract_zip(zip_path: str, extract_to: str):
    """Extracts the contents of a ZIP file to a specified directory and adjusts permissions for executables.

    Args:
        zip_path (str): Path to the ZIP file.
        extract_to (str): Directory to extract contents into.
    """
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

    for item in os.listdir(extract_to):
        item_path = os.path.join(extract_to, item)
        if os.path.isdir(item_path) and "chrome-headless-shell" in item:
            new_folder_name = "chrome-headless-shell"
            new_folder_path = os.path.join(extract_to, new_folder_name)
            os.rename(item_path, new_folder_path)
            break

    if platform.system() != "Windows":
        for root, _, files in os.walk(extract_to):
            for file in files:
                file_path = os.path.join(root, file)
                os.chmod(file_path, os.stat(file_path).st_mode | stat.S_IEXEC)


async def get_last_known_good_release_for_channel(channel: ChromeReleaseChannel) -> dict:
    """Retrieves the last known good release for a specific Chrome channel.

    Args:
        channel (ChromeReleaseChannel): The release channel.

    Returns:
        dict: Version and revision of the last known good release.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(CHROME_LAST_KNOWN_GOOD_VERSION) as response:
            response.raise_for_status()
            data = await response.json()
            channels = data.get("channels", {})
            channel_data = channels.get(channel.value, {})
            return {
                "version": channel_data.get("version"),
                "revision": channel_data.get("revision"),
            }


async def resolve_build_id(channel: ChromeReleaseChannel) -> str:
    """Resolves the build ID for a specific Chrome release channel.

    Args:
        channel (ChromeReleaseChannel): The release channel.

    Returns:
        str: Build ID.
    """
    release_info = await get_last_known_good_release_for_channel(channel)
    return release_info["version"]


def relative_executable_path(platform: BrowserPlatform) -> str:
    """Returns the relative path to the Chrome Headless executable.

    Args:
        platform (BrowserPlatform): The platform enum value.
        build_id (str): The build ID.

    Returns:
        str: Relative path to the executable.

    Raises:
        ValueError: If the platform is unsupported.
    """
    executable_file = "chrome-headless-shell"
    if platform in [BrowserPlatform.WIN32, BrowserPlatform.WIN64]:
        executable_file += ".exe"

    return os.path.join("chrome-headless-shell", executable_file)


def find_executable_path(extract_to: str, platform: BrowserPlatform) -> str:
    """Finds the absolute path to the Chrome Headless executable.

    Args:
        extract_to (str): Directory where the Chrome Headless build is extracted.
        platform (BrowserPlatform): The platform enum value.

    Returns:
        str: Absolute path to the executable.
    """
    relative_path = relative_executable_path(platform)
    absolute_path = os.path.abspath(os.path.join(extract_to, relative_path))
    if not os.path.exists(absolute_path):
        raise FileNotFoundError(f"Executable not found at {absolute_path}")

    return absolute_path


def main(browser_platform: BrowserPlatform, channel: ChromeReleaseChannel, output_path: str):
    """Main function to handle Chrome Headless download and extraction.

    Args:
        browser_platform (BrowserPlatform): The platform enum value.
        channel (ChromeReleaseChannel): The release channel.
        output_path (str): Directory to extract the Chrome Headless build into.

    Raises:
        FileNotFoundError: If the executable is not found.

    Returns:
        str: Absolute path to the Chrome Headless executable.
    """
    async def async_main():
        with tempfile.TemporaryDirectory() as download_directory:
            ensure_directory_exists(output_path)

            build_id = await resolve_build_id(channel)
            url = resolve_download_url(browser_platform, build_id)
            download = os.path.join(download_directory, os.path.basename(url))

            await download_file(url, download)
            extract_zip(download, output_path)

            executable_path = find_executable_path(output_path, browser_platform)
            print(executable_path)  # noqa: T201

    import asyncio
    asyncio.run(async_main())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "This script downloads and extracts Chrome Headless builds for testing purposes. "
            "It identifies the current operating system, determines the appropriate Chrome Headless build "
            "based on the specified release channel, and extracts the binary to a specified directory."
        ),
        epilog="Example usage: python download-chrome-headless-shell.py --output ./chrome-bin",
    )

    parser.add_argument(
        "-b",
        "--browser_platform",
        type=BrowserPlatform,
        required=False,
        default=BrowserPlatform.identify_current_os(),
        help=(
            "Specify the target browser platform for the Chrome Headless build. "
            "Defaults to the platform detected on the current system."
        ),
    )

    parser.add_argument(
        "-c",
        "--channel",
        type=ChromeReleaseChannel,
        required=False,
        default=ChromeReleaseChannel.STABLE,
        help=(
            "Specify the Chrome release channel to download from. "
            "Options: Stable, Beta, Dev, Canary. Defaults to Stable."
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        default=".bin",
        help=("Specify the output directory where the Chrome Headless build will be extracted. Defaults to '.bin'."),
    )

    args = parser.parse_args()

    main(browser_platform=args.browser_platform, channel=args.channel, output_path=args.output)
