import sys
import pathlib
import webbrowser
import customtkinter as ctk
import threading
from CTkMessagebox import CTkMessagebox
from PIL import Image

from Windows import *
from Model.Server import *

class App(ctk.CTk):
    DEFAULT_FG_COLOR = ("#dbdbdb", '#2b2b2b')
    SELECT_GRAY = ("gray50", "gray30")
    TEXT_COLOR = ('black', 'white')

    WIDTH = 800
    HEIGHT = 600

    def __init__(self):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.__on_close)
        if sys.platform.startswith("win"):
            import ctypes
            myappid = u"serverlauncher.1.0.0"  # 隨便唯一字串
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        # Load icon
        icon_image_path = pathlib.Path(__file__).parent.joinpath('Windows', 'icon')
        self.img_settings = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('setting_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('setting_dark.png')),
        )
        self.img_settings_dark = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('setting_dark.png')),
            dark_image=Image.open(icon_image_path.joinpath('setting_dark.png')),
        )
        self.img_logo = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('logo_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('logo_dark.png')),
            size=(128, 128)
        )
        self.img_add = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('add_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('add_dark.png')),
        )
        self.img_run = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('run_dark.png')),
            dark_image=Image.open(icon_image_path.joinpath('run_dark.png')),
        )
        self.img_stop = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('stop_dark.png')),
            dark_image=Image.open(icon_image_path.joinpath('stop_dark.png')),
        )

        self.build_ui()

    def build_ui(self):
        # 設定外觀主題
        highlight_font = ctk.CTkFont(size=16)
        ctk.set_appearance_mode("system")  # dark/light/system
        ctk.set_default_color_theme("blue")  # 可換成 "green" 或 "dark-blue"

        self.title("Server Launcher")
        self.geometry(f'{self.WIDTH}x{self.HEIGHT}')
        self.resizable(False, False)

        # --- 左側欄 ---
        self.sidebar = ctk.CTkFrame(self)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)

        self.logo = ctk.CTkLabel(self.sidebar, image=self.img_logo, text='')
        self.logo.pack(pady=(5, 5))

        #新增Server
        self.adding_server_button = ctk.CTkButton(
            master=self.sidebar,
            fg_color=self.DEFAULT_FG_COLOR,
            hover_color=self.SELECT_GRAY,
            text="新增伺服器",
            text_color=self.TEXT_COLOR,
            image=self.img_add,
            command=self.__on_adding_server_clicked,
            font=highlight_font
        )
        self.adding_server_button.pack(pady=(0, 5))

        # 左邊滾動清單
        self.server_list_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color=self.DEFAULT_FG_COLOR, corner_radius=0)
        self.server_list_scroll.pack(fill="both", expand=True, padx = 5, pady=(5, 5))

        self.server_buttons = []
        self.refresh_server_list()
        self.bind("<FocusIn>", lambda e: self.refresh_server_list())

        #設定按鈕
        self.settings_button = ctk.CTkButton(
            master=self.sidebar,
            fg_color=self.DEFAULT_FG_COLOR,
            hover_color=self.SELECT_GRAY,
            text="設定",
            text_color=self.TEXT_COLOR,
            image=self.img_settings,
            command=self.__on_settings_clicked,
            font=highlight_font
        )
        self.settings_button.pack(side="bottom", pady=20)

        # --- 右側主面板 ---
        self.main_panel = ctk.CTkFrame(self)
        self.main_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # 腳本框區塊
        self.server_frame = ctk.CTkFrame(self.main_panel)
        self.server_frame.pack(fill="x", padx=20, pady=10)

        self.server_title = ctk.CTkLabel(self.server_frame, text="請先選擇伺服器", font=("Arial", 18, "bold"))
        self.server_title.pack(pady=(10, 5))

        self.server_desc = ctk.CTkLabel(self.server_frame, text="<伺服器詳細資訊>")
        self.server_desc.pack()

        # 控制按鈕
        self.controls_frame = ctk.CTkFrame(self.server_frame, fg_color="transparent")
        self.controls_frame.pack(pady=10)

        self.play_button = ctk.CTkButton(
            master=self.controls_frame,
            text="執行",
            image=self.img_run,
            command=self.__on_server_run_clicked,
            width=100,
        )
        self.play_button.grid(row=0, column=0, padx=10)

        self.options_button = ctk.CTkButton(
            master=self.controls_frame,
            text="設定",
            fg_color="orange",
            hover_color='#BF7C00',
            image=self.img_settings_dark,
            command=self.__on_server_option_clicked,
            width=100,
        )
        self.options_button.grid(row=0, column=1, padx=10)

        # Log 區塊
        self.log_frame = ctk.CTkFrame(self.main_panel)
        self.log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.log_title = ctk.CTkLabel(self.log_frame, text="Log", font=("Arial", 16))
        self.log_title.pack(pady=5)

        log_font = ctk.CTkFont(size=10)

        self.log_textbox = ctk.CTkTextbox(self.log_frame, font=log_font)
        self.log_textbox.configure(state="disabled")
        self.log_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        # 指令輸入區
        self.command_frame = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        self.command_frame.pack(fill="x", padx=5, pady=(0, 5))

        self.command_entry = ctk.CTkEntry(self.command_frame, placeholder_text="輸入指令後按 Enter 或點送出")
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.command_entry.bind('<Return>', self.__on_command_submit)  # 支援Enter

        self.send_button = ctk.CTkButton(
            self.command_frame,
            text="送出",
            width=60,
            command=self.__on_command_submit
        )
        self.send_button.pack(side="right")
        
        servers = ServerManager().list_servers()
        if servers:
            self.__on_server_selected(servers[0])

    def refresh_server_list(self):
        # 清空舊的按鈕
        for btn in getattr(self, "server_buttons", []):
            btn.destroy()
        self.server_buttons = []

        servers = ServerManager().list_servers()
        if len(servers) < 9:
            self.server_list_scroll._scrollbar.configure(width=0)
        else:
            self.server_list_scroll._scrollbar.configure(width=1)
        for name in servers:
            btn = ctk.CTkButton(
                self.server_list_scroll, 
                text=name, 
                fg_color=self.DEFAULT_FG_COLOR,
                hover_color=self.SELECT_GRAY,
                text_color=self.TEXT_COLOR,
                command=lambda name=name: self.__on_server_selected(name),
            )
            btn.pack(pady=5, padx=5)
            self.server_buttons.append(btn)

    def log_to_ui(self, line):
        self.log_textbox.configure(state="normal")   # 解鎖
        self.log_textbox.insert("end", line)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled") # 鎖回

    # ---------- Event --------- #
    def __on_settings_clicked(self):
        CTkMessagebox(title="提示", message="加班施工中...\n請稍後再來", icon="warning")
        # SettingWindow(parent=self)
        
    def __on_adding_server_clicked(self):
        NewServerWindow(parent=self)

    def __on_server_selected(self, server_name):
        if hasattr(self, "server") and self.server is not None and self.server.is_running():
            CTkMessagebox(
                title="禁止切換伺服器",
                message="請先關閉目前正在運行的伺服器，才能切換伺服器！",
                icon="warning"
            )
            return
        self.server = ServerManager().get_server(server_name, callback_log=self.log_to_ui)
        self.server_title.configure(text=server_name)
        self.server_desc.configure(text=f'伺服器種類: {self.server.name}, 版本: {self.server.version}')

    def __on_server_run_clicked(self):
        # 假設有選到server才執行
        if not hasattr(self, "server") or self.server is None:
            CTkMessagebox(title="提示", message="請先選擇伺服器", icon="warning")
            return
        if not self.server.is_running():
            # 檢查EULA狀態
            if not self.server.get_eula_status():
                # 彈窗詢問
                result = CTkMessagebox(
                    title="EULA 條款未同意",
                    message="您尚未簽屬EULA條款，無法啟動伺服器。\n是否已經閱讀並同意？",
                    icon="warning",
                    option_3="閱讀EULA條款",
                    option_2="同意",
                    option_1="不同意"
                ).get()
                if result == "閱讀EULA條款":
                    webbrowser.open("https://account.mojang.com/documents/minecraft_eula")
                    return
                elif result == "同意":
                    self.server.set_eula(True)
                elif result == "不同意":
                    return
            
            self.server.start()
            self.play_button.configure(text="停止", image=self.img_stop, fg_color = '#E63F39', hover_color='#C43631')
        else:
            def stop_and_update():
                self.server.stop()
                self.play_button.configure(text="啟動", image=self.img_run, fg_color = '#3B8ED0', hover_color='#36719f')
            threading.Thread(target=stop_and_update, daemon=True).start()

    def __on_server_option_clicked(self):
        CTkMessagebox(title="提示", message="加班施工中...\n請稍後再來", icon="warning")

    def __on_command_submit(self, event=None):
        cmd = self.command_entry.get().strip()
        if cmd and self.server and self.server.is_running():
            self.server.send_command(cmd)
            self.log_textbox.insert("end", f"> {cmd}\n")
            self.command_entry.delete(0, "end")

    def __on_close(self):
        if hasattr(self, "server") and self.server and self.server.is_running():
            answer = CTkMessagebox(
                title="確認離開",
                message="確定要離開 Server Launcher 嗎？\n你的Server還沒關閉",
                icon="question",
                option_1="是",
                option_2="否"
            ).get()
            if answer == "是":
                # 可以先執行安全關閉伺服器
                try:
                    self.server.stop()
                except Exception:
                    pass
                self.destroy()
            else:
                # 什麼都不做，視窗不會關
                return
        else:
            self.destroy()

    # ---------- Other methode ---------- #
    def center_window(self):
        # 取得螢幕寬高
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # 計算 x, y 座標
        x = (screen_width // 2) - (self.WIDTH // 2)
        y = (screen_height // 2) - (self.HEIGHT // 2)

        # 設定視窗位置
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

if __name__ == "__main__":
    app = App()
    app.center_window()
    app.mainloop()
