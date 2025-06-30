from abc import ABC, abstractmethod
from typing import List

class BaseServer(ABC):
    name: str
    _running: bool
    
    def __init__(self, path, callback_log):
        self.path = path

    @abstractmethod
    def set_eula(self, able):
        """
        設定Server的EULA狀態
        """

    @abstractmethod
    def get_eula_status() -> bool:
        """
        檢查Server的EULA狀態
        """

    def is_running(self) -> bool:
        """
        伺服器狀態 True for running
        """

    @abstractmethod
    def start(self):
        """
        啟動Server
        """

    @abstractmethod
    def stop(self):
        """
        停止Server
        """
