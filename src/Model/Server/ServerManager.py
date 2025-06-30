import os

from .BaseServer import BaseServer
from .ServerFactory import ServerFactory
from Model.Config import Config

class ServerManager:
    def __init__(self):
        self.base_path = Config().app_folder

    def list_servers(self):
        # 回傳所有 server 資料夾名稱，依建立時間排序（新到舊）
        servers = [
            d for d in os.listdir(self.base_path)
            if os.path.isdir(os.path.join(self.base_path, d)) and d != 'Java'
        ]
        servers.sort(
            key=lambda d: os.path.getctime(os.path.join(self.base_path, d)), 
            reverse=True  # 新→舊，如果要舊→新就 reverse=False
        )
        return servers

    def get_server(self, server_name, callback_log) -> BaseServer:
        server_path = os.path.join(self.base_path, server_name)
        if not os.path.isdir(server_path):
            raise FileNotFoundError(f"Server '{server_name}' does not exist.")
        return ServerFactory.create(server_path, callback_log)
