import pathlib

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from PIL import Image

class SettingWindow(ctk.CTkToplevel):
    WIDTH, HEIGHT = 640, 480

    DEFAULT_FG_COLOR = ("#dbdbdb", '#2b2b2b')
    SELECT_GRAY = ("gray50", "gray30")
    TEXT_COLOR = ('black', 'white')

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Settings")
        self.geometry(f'{self.WIDTH}x{self.HEIGHT}')
        self.center_window()
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        # Load icon
        icon_image_path = pathlib.Path(__file__).parent.joinpath('icon')
        self.img_settings = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('info_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('info_dark.png')),
        )
        self.img_java = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('java_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('java_dark.png')),
        )
        self.img_language = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('language_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('language_dark.png')),
        )
        self.img_infomation = ctk.CTkImage(
            light_image=Image.open(icon_image_path.joinpath('info_light.png')),
            dark_image=Image.open(icon_image_path.joinpath('info_dark.png')),
        )

        self.build_ui()

    def build_ui(self):
        self.rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        highlight_font = ctk.CTkFont(size=20)
        # 左邊選單列
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        ctk.CTkLabel(self.sidebar, text="設定選單",font=highlight_font).grid(row=0, column=0, pady=20)
        self.buttons = [
            {
                'name': '一般',
                'command': self.show_general,
                'image': self.img_settings,
            },
            {
                'name': 'Java',
                'command': self.show_java,
                'image': self.img_java,
            },
            {
                'name': '語言',
                'command': self.show_language,
                'image': self.img_language,
            },
            {
                'name': '關於',
                'command': self.show_about,
                'image': self.img_infomation,
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

        self.show_general()  # 預設顯示「一般」

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

    def show_general(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="一般設定", font=ctk.CTkFont(size=20)).pack(pady=20)
        ctk.CTkCheckBox(self.content_frame, text="啟用自動更新").pack(pady=10)
        ctk.CTkCheckBox(self.content_frame, text="啟用通知").pack(pady=10)

    def show_java(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Java 設定", font=ctk.CTkFont(size=20)).pack(pady=20)
        ctk.CTkLabel(self.content_frame, text="選擇版本：").pack()
        ctk.CTkOptionMenu(self.content_frame, values=["Java 8", "Java 17", "Java 21"]).pack(pady=10)

    def show_language(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="語言設定", font=ctk.CTkFont(size=20)).pack(pady=20)
        self.language_menu = ctk.CTkOptionMenu(
            self.content_frame, 
            values=["繁體中文", "English (Unavailable)", "日本語 (Unavailable)"],
            command=self.handle_language_select
        )
        self.language_menu.pack(pady=10)
        self.language_menu.set("繁體中文")

    def show_about(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="關於本程式", font=ctk.CTkFont(size=20)).pack(pady=20)

    # Handel Option Menu event
    def handle_language_select(self, choice):
        if choice != "繁體中文":
            CTkMessagebox(title="提示", message="目前僅支援『繁體中文』", icon="warning")
            self.language_menu.set("繁體中文")
        