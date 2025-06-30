import os
import platform
import zipfile
import shutil
from pathlib import Path

import requests

from .Config import Config

class JavaDownloader:
    recommended_versions = ['8', '17', '21']

    def __init__(self):
        config = Config()
        default_dir = os.path.join(config.app_folder, 'Java')
        self.save_dir = Path(config.get_and_save('java.dir', default_dir))
        self.os_map = {
            "Windows": "windows",
            "Linux": "linux",
            "Darwin": "mac"
        }
        self.arch_map = {
            "x86_64": "x64",
            "AMD64": "x64",
            "aarch64": "aarch64"
        }

    def _fetch_supported_versions(self, lts_only: bool = False) -> list:
        url = "https://api.adoptium.net/v3/info/available_releases"
        try:
            res = requests.get(url)
            data = res.json()
            return data["available_lts_releases"] if lts_only else data["available_releases"]
        except Exception as e:
            print(f"取得版本資訊失敗：{e}")
            return [8, 11, 17, 21]  # 預設備援版本

    def _get_platform(self):
        os_name = self.os_map.get(platform.system(), "windows")
        arch = self.arch_map.get(platform.machine(), "x64")
        return os_name, arch

    def _get_download_url(self, version: int, os_name: str, arch: str) -> str:
        base_url = "https://api.adoptium.net/v3/binary/latest"
        return f"{base_url}/{version}/ga/{os_name}/{arch}/jre/hotspot/normal/eclipse"

    def _extract_zip_flatten(self, zip_path: Path, extract_path: Path, progress_callback=None):
        extract_path = Path(extract_path)
        if extract_path.exists():
            shutil.rmtree(extract_path)
        extract_path.mkdir(parents=True, exist_ok=True)

        temp_dir = extract_path.parent / (extract_path.name + "_tmp")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 解壓縮 zip（支援 progress_callback）
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            names = zip_ref.namelist()
            total = len(names)
            for idx, member in enumerate(names, 1):
                zip_ref.extract(member, temp_dir)
                if progress_callback:
                    persant = int(idx/total*100)
                    progress_callback(persant)

        # 找到唯一的一層目錄（如 jdk-21.0.7+6-jre）
        items = list(temp_dir.iterdir())
        if len(items) == 1 and items[0].is_dir():
            top_dir = items[0]
            for child in top_dir.iterdir():
                shutil.move(str(child), str(extract_path))
            shutil.rmtree(temp_dir)
            print(f"已展平成：{extract_path}")
        else:
            for item in items:
                shutil.move(str(item), str(extract_path))
            shutil.rmtree(temp_dir)
            print(f"已解壓縮至：{extract_path}")

        return extract_path

    def download(self, version: int, extract=True, extract_to: str = None, progress_callback=None):
        supported_versions = self._fetch_supported_versions()
        if version not in supported_versions:
            raise ValueError(f"版本 {version} 不支援，支援版本為: {supported_versions}")

        os_name, arch = self._get_platform()
        url = self._get_download_url(version, os_name, arch)
        zip_path = self.save_dir / f"OpenJRE{version}.zip"

        # 步驟1：下載
        if not zip_path.exists() or not zipfile.is_zipfile(zip_path):
            print(f"下載 Java {version} JRE: {url}")
            self.save_dir.mkdir(parents=True, exist_ok=True)
            response = requests.get(url, stream=True, allow_redirects=True)
            if response.status_code != 200:
                raise Exception(f"下載失敗 (HTTP {response.status_code})")
            total_length = int(response.headers.get('content-length', 0))
            chunk_size = 65536  # 64KB
            downloaded = 0
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_length:
                            percent = downloaded / total_length * 100
                            # 下載佔 0-70%
                            progress_callback(percent * 0.7)
            print(f"已下載：{zip_path}")
        else:
            print(f"已存在壓縮檔：{zip_path}")
            if progress_callback:
                progress_callback(70)  # 下載步驟直接標記 70%

        # 步驟2：解壓縮
        if extract:
            if not extract_to:
                raise ValueError("extract_to 參數必須指定解壓縮資料夾")
            # 建立一個 70~100% 的 callback
            if progress_callback:
                extract_progress_cb = make_weighted_progress_callback(70, 100, progress_callback)
            else:
                extract_progress_cb = None
            return self._extract_zip_flatten(zip_path, extract_to, progress_callback=extract_progress_cb)
        return zip_path
    
def make_weighted_progress_callback(start_weight, end_weight, global_callback):
    """
    global_callback: 寫總進度的callback (0~100)
    start_weight: 本步驟佔總進度的起始百分比 (例如0, 20, 70)
    end_weight:   本步驟佔總進度的結束百分比 (例如20, 70, 100)
    """
    def weighted_callback(local_percent):
        # local_percent: 本步驟內的百分比(0~100)
        global_percent = start_weight + (end_weight - start_weight) * (local_percent / 100)
        global_callback(global_percent)
    return weighted_callback


if __name__ == "__main__":
    downloader = JavaDownloader()
    # 範例：下載 Java 17，解壓縮到 D:/Work/MyJava17
    downloader.download(17, extract=True, extract_to="D:/Work/MyJava17")
