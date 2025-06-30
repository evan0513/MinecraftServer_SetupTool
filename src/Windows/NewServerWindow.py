import pathlib
import threading

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from PIL import Image

from .AddingServerWindows import show_progress_and_do_task
from Model.Downloader.DownloaderFactory import DownloaderFactory
from Model.Java import JavaDownloader
from Model.Server.ServerManager import ServerManager

INVALID_CHARS = r'\/:*?"<>|'

class NewServerWindow(ctk.CTkToplevel):
    WIDTH, HEIGHT = 640, 480

    DEFAULT_FG_COLOR = ("#dbdbdb", '#2b2b2b')
    HIGHLIGHT_FG_COLOR = ("#B5B5B5", "#525252")
    SELECT_GRAY = ("gray50", "gray30")
    TEXT_COLOR = ('black', 'white')

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.server_config = {
            'name': None,
            'server.type': None,
            'server.version': None,
            'java.version': None,
        }
        # Windows init
        self.title("Adding Servers")
        self.geometry(f'{self.WIDTH}x{self.HEIGHT}')
        self.center_window()
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        # Load icon
        icon_image_path = pathlib.Path(__file__).parent.joinpath('icon')
        self.img_general = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('info_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('info_dark.png')),
        )
        self.img_version = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('version_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('version_dark.png')),
        )
        self.img_java = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('java_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('java_dark.png')),
        )

        self.build_ui()

    def build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(1, weight=1)
        highlight_font = ctk.CTkFont(size=20)
        # 左邊選單列
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        ctk.CTkLabel(self.sidebar, text="選項",font=highlight_font).grid(row=0, column=0, pady=20)
        self.buttons = [
            {
                'name': '一般',
                'command': self.show_general,
                'image': self.img_general,
            },
            {
                'name': '版本',
                'command': self.show_version,
                'image': self.img_version,
            },
            {
                'name': 'Java',
                'command': self.show_java,
                'image': self.img_java,
            }
        ]
        for (i, bottom_info) in enumerate(self.buttons, start=1):
            btn = ctk.CTkButton(
                master=self.sidebar,
                fg_color=self.DEFAULT_FG_COLOR,
                hover_color=self.SELECT_GRAY,
                text=bottom_info['name'],
                font=highlight_font,
                text_color=self.TEXT_COLOR,
                image=bottom_info['image'],
                command=bottom_info['command'],
            )
            btn.grid(row=i, column=0, padx=20, pady=10, sticky="ew")

        # 右側內容Frame
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.show_general()  # 預設顯示「版本」

        # TODO: 右下方確定項
        self.bottom_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.bottom_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 10))

        self.confirm_button = ctk.CTkButton(
            self.bottom_frame,
            text="儲存",
            command=self.add_server,
            fg_color="#3B82F6",
            text_color="white",
            hover_color="#2563EB"
        )
        self.confirm_button.pack(side="right", padx=(0, 10))

        self.cancel_button = ctk.CTkButton(
            self.bottom_frame,
            text="取消",
            command=self.destroy,
            fg_color="#9CA3AF",
            text_color="white",
            hover_color="#6B7280"
        )
        self.cancel_button.pack(side="right", padx=(0, 10))


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

    # 清除右側內容
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # 刷新右側內容
    # ---------- 一般設定 ----------
    def show_general(self):
        self.clear_content()
        top_bar = ctk.CTkFrame(self.content_frame, fg_color=self.DEFAULT_FG_COLOR)
        top_bar.pack(side="top", fill="x", pady=10, padx=(10, 10))
        ctk.CTkLabel(top_bar, text="一般設定", font=ctk.CTkFont(size=20)).pack(side="left")

        # 名字輸入區塊
        input_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=10, padx=30)

        ctk.CTkLabel(input_frame, text="名字(可空白)：", font=ctk.CTkFont(size=16), anchor="w").grid(row=0, column=0, sticky="w")
        self.name_var = ctk.StringVar(value=self.server_config.get('server.name', ''))
        name_entry = ctk.CTkEntry(input_frame, textvariable=self.name_var, width=200)
        name_entry.grid(row=0, column=1, sticky="e")

        # 讓輸入框靠右
        input_frame.grid_columnconfigure(0, weight=1)  # 左側（label）自動填滿
        input_frame.grid_columnconfigure(1, weight=0)  # 右側（entry）緊靠右
    # ---------- 選擇版本 ----------
    def show_version(self):
        self.clear_content()

        top_bar = ctk.CTkFrame(self.content_frame, fg_color=self.DEFAULT_FG_COLOR)
        top_bar.pack(side="top", fill="x", pady=10, padx=(10, 10))

        ctk.CTkLabel(top_bar, text="版本", font=ctk.CTkFont(size=20)).pack(side="left")

        server_type = DownloaderFactory.list_available_types()
        self.java_version_var = ctk.StringVar(value=server_type[0])
        self.version_type_menu = ctk.CTkOptionMenu(
            top_bar,
            values=server_type,
            variable=self.java_version_var,
            command=self.on_server_type_change,
            fg_color=self.HIGHLIGHT_FG_COLOR,
            button_color =self.HIGHLIGHT_FG_COLOR,
            button_hover_color =self.HIGHLIGHT_FG_COLOR,
            text_color=self.TEXT_COLOR,
            width=120
        )
        self.version_type_menu.pack(side="right")

        ctk.CTkLabel(top_bar, text="選擇版本：").pack(side="right")

        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text="版本", width=100, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 0))
        ctk.CTkLabel(header, text="發行日期", width=100, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="right", padx=5)
        ctk.CTkLabel(header, text="類型", width=100, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="right", padx=5)

        self.scrollable = ctk.CTkScrollableFrame(self.content_frame, fg_color=self.DEFAULT_FG_COLOR)
        self.scrollable.pack(fill="both", expand=True, padx=0, pady=(0, 5))
        self.selected_row = None
        if self.server_config['server.type'] is None:
            self.on_server_type_change(server_type[0])
        else:
            self.on_server_type_change(self.server_config['server.type'])

    def on_server_type_change(self, selected_type):
        print(f"選擇Server種類: {selected_type}")
        self.server_config['server.type'] = selected_type
        for widget in self.scrollable.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.scrollable, text="載入版本資料中...", font=ctk.CTkFont(size=18)).pack()
        thread = threading.Thread(target=self.load_server_verion, args=(selected_type,))
        self.after(100, lambda: thread.start())
        
    def load_server_verion(self, selected_type):
        downloader = DownloaderFactory.create_downloader(selected_type)
        version_data = downloader.get_verions_list()

        self.after(0, lambda: self.display_versions(version_data))

    def display_versions(self, version_data):
        for widget in self.scrollable.winfo_children():
            widget.destroy()
        
        self.rows = []
        for data in version_data:
            row = SelectableTableRow(
                self.scrollable, *data, on_select=self.on_row_selected
            )
            row.pack(fill="x", pady=0.5)
            self.rows.append(row)
            
        if self.server_config['server.version'] is None:
            self.after(10, lambda:self.on_row_selected(self.rows[0]))
        else:
            row = next(row for row in self.rows if row.version == self.server_config['server.version'])
            self.after(10, lambda:self.on_row_selected(row))

    def on_row_selected(self, row):
        print(f"選取Server版本: {row.version}")
        self.server_config['server.version'] = row.version
        if self.selected_row:
            self.selected_row.set_selected(False)
        self.selected_row = row
        row.set_selected(True)
    # ---------- Java設定 ----------
    def show_java(self):
        self.clear_content()

        top_bar = ctk.CTkFrame(self.content_frame, fg_color=self.DEFAULT_FG_COLOR)
        top_bar.pack(side="top", fill="x", pady=10, padx=(10, 10))

        ctk.CTkLabel(top_bar, text="Java設定", font=ctk.CTkFont(size=20)).pack(side="left")

        java_version =  ['自動'] + JavaDownloader.recommended_versions
        self.java_version_var = ctk.StringVar(value=java_version[0])
        self.version_type_menu = ctk.CTkOptionMenu(
            top_bar,
            values=java_version,
            variable=self.java_version_var,
            command=self.on_java_version_change,
            fg_color=self.HIGHLIGHT_FG_COLOR,
            button_color =self.HIGHLIGHT_FG_COLOR,
            button_hover_color =self.HIGHLIGHT_FG_COLOR,
            text_color=self.TEXT_COLOR,
            width=120,
        )
        self.version_type_menu.pack(side="right")

        ctk.CTkLabel(top_bar, text="選擇版本：").pack(side="right")
    
    def on_java_version_change(self, version):
        print(f"選取Java版本: {version}")
        if version == '自動':
            self.server_config['java.version'] = None
        else:
            self.server_config['java.version'] = version

    # ---------- 創建Server ----------
    def add_server(self):
        # 取得名字
        server_name = self.name_var.get()
        if not self.is_valid_server_name(server_name):
            CTkMessagebox(
                title="錯誤",
                message="伺服器名稱不可包含以下字元：\n\\ / : * ? \" < > |\n也不能以空白開頭或結尾。",
                icon="cancel"
            )
            return

        if not self.server_config['name'] is None:
            if len(self.server_config['name'].strip()) == 0:
                self.server_config['name'] = None
        
        show_progress_and_do_task(self, self.server_config)

    # ---------- 其他method ----------
    def is_valid_server_name(self, name: str) -> bool:
        # 空字串直接合法
        if not name.strip():
            return True
        # 只要有非法字元、或開頭結尾是空白就不行
        if any(char in INVALID_CHARS for char in name):
            return False
        if name[0] == " " or name[-1] == " ":
            return False
        return True


class SelectableTableRow(ctk.CTkFrame):
    def __init__(self, master, version, date, type_, is_selected=False, on_select=None, **kwargs):
        super().__init__(master, **kwargs)
        self.version = version
        self.date = date
        self.type_ = type_
        self.on_select = on_select
        self.selected = is_selected

        self.configure(height=30)
        self.pack_propagate(False)

        self.label_version = ctk.CTkLabel(self, text=version, anchor="w")
        self.label_version.pack(side="left", fill="x", expand=True, padx=(10, 0))

        self.label_date = ctk.CTkLabel(self, text=date, width=100, anchor="w")
        self.label_date.pack(side="right", padx=5)

        self.label_type = ctk.CTkLabel(self, text=type_, width=80, anchor="w")
        self.label_type.pack(side="right", padx=5)

        self.bind("<Button-1>", self.select)
        self.label_version.bind("<Button-1>", self.select)
        self.label_date.bind("<Button-1>", self.select)
        self.label_type.bind("<Button-1>", self.select)

        self.update_color()

    def select(self, event=None):
        if self.on_select:
            self.on_select(self)

    def set_selected(self, selected):
        self.selected = selected
        self.update_color()

    def update_color(self):
        bg_color = "#4a4a4a" if self.selected else "transparent"
        self.configure(fg_color=bg_color)

    def set_selected(self, selected):
        self.selected = selected
        self.update_color()
    
    def update_color(self):
        bg_color = "#818181" if self.selected else "transparent"
        self.configure(fg_color=bg_color)

    