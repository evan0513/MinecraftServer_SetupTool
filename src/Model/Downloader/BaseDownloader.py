from abc import ABC, abstractmethod
from typing import List

class BaseDownloader(ABC):
    name: str
    latest_version: str

    @abstractmethod
    def get_verions_list(self, snapshot = False) -> List[List[str]]:
        """
        列出所有可下載的版本字串，例如 ['1.20.6', '1.20.5', '1.19.4']
        - snapshot: 是否列出快照
        """
    
    @abstractmethod
    def get_latest_version(self) -> str:
        """
        取得最新穩定版本，例如 '1.20.6'
        """

    @abstractmethod
    def get_java_version(self, version: str) -> str:
        """
        取得對應版本的Java版本，例如 '21'
        """

    @abstractmethod
    def download(self, version: str, path: str, progress_callback=None) -> None:
        """
        下載指定版本的 server 到指定路徑
        - version: Minecraft server 版本，例如 '1.20.6'
        - path: 儲存 jar 檔的完整檔案路徑，例如 './servers/vanilla-1.20.6.jar'
        - progress_callback: Callback進度的，變數使用百分比，例如 callback(80)
        """
        ...
