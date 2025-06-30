from .BaseDownloader import BaseDownloader

from .VanillaDownloader import VanillaDownloader

class DownloaderFactory:
    _downloader_classes = {}

    @classmethod
    def _load_subclasses(cls):
        # 自動註冊所有 BaseDownloader 子類別
        for subclass in BaseDownloader.__subclasses__():
            if not hasattr(subclass, "name"):
                continue
            # 獲取名稱
            cls._downloader_classes[subclass.name] = subclass

    @classmethod
    def list_available_types(cls):
        if not cls._downloader_classes:
            cls._load_subclasses()
        types = list(cls._downloader_classes.keys())
        if 'Vanilla' in types:
            types.remove('Vanilla')
            types.insert(0, 'Vanilla')
        return types

    @classmethod
    def create_downloader(cls, server_type: str) -> BaseDownloader:
        if not cls._downloader_classes:
            cls._load_subclasses()
        # server_type = server_type.lower()
        if server_type not in cls._downloader_classes:
            raise ValueError(f"Unsupported server type: {server_type}")
        return cls._downloader_classes[server_type]()