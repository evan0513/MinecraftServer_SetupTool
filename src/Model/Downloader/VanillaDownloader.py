import threading
from typing import List
from concurrent.futures import ThreadPoolExecutor

import requests

from .BaseDownloader import BaseDownloader

class VanillaDownloader(BaseDownloader):
    name = "Vanilla"

    def __init__(self):
        super().__init__()
        self.latest_version = None
        self.manifest = None

    def get_verions_list(self, snapshot=False) -> List[List[str]]:
        self.manifest = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json").json()
        self.latest_version = self.manifest['latest']['release']
        if snapshot:
            versions = [[version['id'], version['type'], version['releaseTime'][:10]] for version in self.manifest['versions']]
        else:
            versions = [[version['id'], version['type'], version['releaseTime'][:10]] for version in self.manifest['versions'] if version['type'] == "release"]
        return versions
    
    def get_latest_version(self) -> str:
        if self.latest_version is None:
            self.get_verions_list()
        return self.latest_version
    
    def get_java_version(self, version: str) -> str:
        if self.manifest is None:
            self.get_verions_list()
    
        item = next((v for v in self.manifest["versions"] if v["id"] == version), None)
        if item is None:
            raise ValueError(f"Version {version} not found.")
        detail = requests.get(item["url"]).json()
        if detail['javaVersion'].get('majorVersion') is None:
            raise ValueError(f"Version {version} java not found.")
        return detail['javaVersion'].get('majorVersion')

    def download(self, version, path, progress_callback=None, num_threads=16):
        if self.manifest is None:
            self.get_verions_list()

        item = next(v for v in self.manifest["versions"] if v["id"] == version)
        detail = requests.get(item["url"]).json()
        jar_url = detail["downloads"]["server"]["url"]
        r = requests.head(jar_url)
        total_length = int(r.headers.get('content-length', 0))

        if "accept-ranges" not in r.headers or r.headers["accept-ranges"] != "bytes":
            # 伺服器不支援 Range，回退單線程
            return self._single_thread_download(jar_url, path, progress_callback, total_length)
        
        part_size = total_length // num_threads

        # 用來記錄進度
        progress = [0] * num_threads
        lock = threading.Lock()
        chunk_size = 65536  # 64KB

        def download_range(idx, start, end):
            headers = {"Range": f"bytes={start}-{end}"}
            resp = requests.get(jar_url, headers=headers, stream=True)
            with open(f"{path}.part{idx}", "wb") as f:
                for chunk in resp.iter_content(chunk_size):
                    if chunk:
                        f.write(chunk)
                        with lock:
                            progress[idx] += len(chunk)
                            if progress_callback:
                                percent = int(sum(progress) / total_length * 100)
                                progress_callback(percent)

        # 排列好每個 thread 的下載範圍
        futures = []
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            for i in range(num_threads):
                start = part_size * i
                end = total_length - 1 if i == num_threads - 1 else (start + part_size - 1)
                futures.append(executor.submit(download_range, i, start, end))

            for f in futures:
                f.result()  # 等所有 thread 結束

        # 合併所有 part
        with open(path, "wb") as outfile:
            for i in range(num_threads):
                part_path = f"{path}.part{i}"
                with open(part_path, "rb") as infile:
                    outfile.write(infile.read())

        # 刪除 part 檔
        import os
        for i in range(num_threads):
            os.remove(f"{path}.part{i}")

    def _single_thread_download(self, url, path, progress_callback, total_length):
        r = requests.get(url, stream=True)
        chunk_size = 65536  # 64KB
        downloaded = 0
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_length:
                        percent = int(downloaded / total_length * 100)
                        progress_callback(percent)