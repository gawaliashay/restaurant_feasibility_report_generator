# src\rag\downloader.py

from pathlib import Path
from urllib.parse import urlparse

import requests

from src.logging_exception.logging.logger import logging


class Downloader:
    """
    Download regulation PDFs from official sources. 
    output_dir = "data/raw/sourced_docs"
    """

    def __init__(
        self,
        timeout: int = 60
    ) -> None:

        self.timeout = timeout

    def download(
        self,
        url: str,
        output_dir: str | Path
    ) -> Path:

        output_dir = Path(output_dir)

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        filename = Path(
            urlparse(url).path
        ).name

        output_file = output_dir / filename

        logging.info(
            f"Downloading: {url}"
        )

        response = requests.get(
            url,
            timeout=self.timeout,
            stream=True
        )

        response.raise_for_status()

        with open(
            output_file,
            "wb"
        ) as file:

            for chunk in response.iter_content(
                chunk_size=8192
            ):
                file.write(chunk)

        logging.info(
            f"Saved: {output_file}"
        )

        return output_file

    def download_multiple(
        self,
        urls: list[str],
        output_dir: str | Path
    ) -> list[Path]:

        downloaded_files = []

        for url in urls:

            try:

                downloaded_files.append(
                    self.download(
                        url=url,
                        output_dir=output_dir
                    )
                )

            except Exception as exc:

                logging.error(
                    f"Failed: {url} | {exc}"
                )

        return downloaded_files