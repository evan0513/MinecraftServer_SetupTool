import os
import json

from .BaseServer import BaseServer
from .VanillaServer import VanillaServer

class ServerFactory:
    _server_classes = {}

    @classmethod
    def _load_subclasses(cls):
        # 自動註冊所有 BaseDownloader 子類別
        for subclass in BaseServer.__subclasses__():
            if not hasattr(subclass, "name"):
                continue
            # 獲取名稱
            cls._server_classes[subclass.name] = subclass

    @classmethod
    def create(cls, server_path, callback_log):
        if not cls._server_classes:
            cls._load_subclasses()

        with open(os.path.join(server_path, "config.json"), 'r') as file:
            server_config = json.loads(file.read())
        
        if server_config['server.type'] not in cls._server_classes:
            raise ValueError("Unknown server type.")
        else:
            return cls._server_classes[server_config['server.type']](server_path, callback_log)
            
