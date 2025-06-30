import os
import threading
import time
import json

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from Model.Config import Config
from Model.Java import JavaDownloader
from Model.Downloader.DownloaderFactory import DownloaderFactory
from Model.Server.ServerManager import ServerManager

class ProgressWindow(ctk.CTkToplevel):
    WIDTH, HEIGHT = 350, 130
    def __init__(self, parent, text="處理中..."):
        super().__init__(parent)
        self.parent = parent
        self.title("進度")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.label = ctk.CTkLabel(self, text=text)
        self.label.pack(pady=5)
        self.transient(parent)
        # 進度條和百分比同一行
        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.pack(pady=5)
        self.progressbar = ctk.CTkProgressBar(frame, width=200)
        self.progressbar.pack(side="left")
        self.percent_label = ctk.CTkLabel(frame, text="0%")
        self.percent_label.pack(side="left", padx=10)
        self.progressbar.set(0)

    def update_progress(self, value):
        self.progressbar.set(value)
        percent = int(value * 100)
        self.percent_label.configure(text=f"{percent}%")

    def set_text(self, text):
        self.label.configure(text=text)

    def center_window(self):
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        win_w = self.WIDTH
        win_h = self.HEIGHT

        x = parent_x + parent_w // 2 - win_w // 2
        y = parent_y + parent_h // 2 - win_h // 2
        self.geometry(f"+{x}+{y}")

# 示範進度條的呼叫方式
def show_progress_and_do_task(parent, server_config: dict):
    progress_win = ProgressWindow(parent, text="初始化...")
    progress_win.center_window()
    progress_win.grab_set()

    def task():
        try:
            def global_callback(percent):
                progress_win.after(0, progress_win.update_progress(percent/100))
            def make_weighted_progress_callback(start_weight, end_weight, global_callback = global_callback):
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

            server_type = server_config.get('server.type')
            if server_type is None:
                server_type = DownloaderFactory.list_available_types()[0]
                server_config['server.type'] = server_type
            downloader = DownloaderFactory.create_downloader(server_type)

            server_version = server_config.get('server.version')
            if server_version is None:
                server_version = downloader.get_latest_version()
                server_config['server.version'] = server_version

            java_version = server_config.get('java.version')
            if java_version is None:
                java_version = downloader.get_java_version(server_version)
                server_config['java.version'] = java_version

            name = server_config.get('name')
            if name is None:
                base_name = f"{server_type}-{server_version}"
                name = base_name
                idx = 1
                # 自動產生不重複的名字
                exist_servers = ServerManager().list_servers()
                while name in exist_servers:
                    name = f"{base_name}-{idx}"
                    idx += 1
                server_config['name'] = name

            server_dir = os.path.join(Config().get_app_folder(), name)
            os.makedirs(server_dir, exist_ok=True)

            # 下載Server
            jar_name = f"{server_type}-{server_version}.jar"
            jar_dir = os.path.join(server_dir, jar_name)
            progress_win.after(0, progress_win.set_text("下載Server..."))
            downloader.download(server_version, jar_dir, make_weighted_progress_callback(0, 40))

            # 下載Java
            java_dir = os.path.join(server_dir, 'java')
            progress_win.after(0, progress_win.set_text("下載Java..."))
            JavaDownloader().download(java_version, True, java_dir, make_weighted_progress_callback(40, 99))

            # 寫入設定
            progress_win.after(0, progress_win.set_text("寫入設定..."))
            # EULA
            server_config['eula'] = False # 啟動需要用戶同意
            eula_dir = os.path.join(server_dir, 'eula.txt')
            with open(eula_dir, 'w') as file:
                file.write('eula=true')
            # 伺服器設定
            config_dir = os.path.join(server_dir, 'config.json')
            with open(config_dir, 'w') as file:
                file.write(json.dumps(server_config))

            # 完成
            progress_win.update_progress(1.0)
            progress_win.set_text("完成！")
            time.sleep(0.5)

            def finish():
                progress_win.update_progress(1.0)
                progress_win.set_text("完成！")
                progress_win.destroy()
                parent.destroy()  # 如果要一併關掉
                CTkMessagebox(title="完成", message="Minecraft Server 已建立！", icon="check")

            progress_win.after(0, finish)

        except Exception as e:
            # 任務失敗，自動刪掉資料夾
            import shutil
            try:
                if os.path.isdir(server_dir):
                    shutil.rmtree(server_dir)
            except Exception:
                pass
            progress_win.after(0, parent.destroy)
            progress_win.after(0, progress_win.destroy)
            CTkMessagebox(title="錯誤", message=f"新增伺服器過程出錯，資料夾已自動刪除。\n錯誤訊息：{e}", icon="cancel")

    threading.Thread(target=task, daemon=True).start()
