from tkinter import messagebox
import customtkinter as ctk
import tkinter as tk
import os
import sys
import requests
import webbrowser
import zipfile
import shutil
import tempfile
import threading
import time
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 自訂下拉式選單
class ScrollableComboBox(ctk.CTkFrame):
    def __init__(self, master, width=200, height=30, dropdown_height=150, **kwargs):
        super().__init__(master, **kwargs)
        self.values = []
        self.var = tk.StringVar(value="")

        self.entry = ctk.CTkEntry(self, textvariable=self.var, width=width, height=height, state="readonly",
                                  font=("微軟正黑體", 13))
        self.entry.pack(fill="x")

        self.btn = ctk.CTkButton(self, text="▼", width=30, height=height, command=self.toggle_dropdown,
                                 font=("微軟正黑體", 12, "bold"))
        self.btn.place(relx=1, rely=0, anchor="ne")

        self.dropdown_height = dropdown_height
        self.is_dropdown_open = False
        self.dropdown_window = None

    def toggle_dropdown(self):
        if self.is_dropdown_open:
            self.close_dropdown()
        else:
            self.open_dropdown()

    def open_dropdown(self):
        if self.dropdown_window:
            return
        self.dropdown_window = tk.Toplevel(self)
        self.dropdown_window.wm_overrideredirect(True)
        self.dropdown_window.wm_geometry("+%d+%d" % (self.winfo_rootx(), self.winfo_rooty() + self.winfo_height()))

        self.listbox = tk.Listbox(self.dropdown_window, height=10, font=("微軟正黑體", 12))
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(self.dropdown_window, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.listbox.delete(0, "end")
        for val in self.values:
            self.listbox.insert("end", val)

        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.dropdown_window.bind("<FocusOut>", lambda e: self.close_dropdown())

        self.is_dropdown_open = True
        self.dropdown_window.focus_set()

    def close_dropdown(self):
        if self.dropdown_window:
            self.dropdown_window.destroy()
            self.dropdown_window = None
        self.is_dropdown_open = False

    def on_select(self, event):
        selected_indices = self.listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            value = self.listbox.get(index)
            self.var.set(value)
            self.close_dropdown()

    def set(self, value):
        self.var.set(value)

    def get(self):
        return self.var.get()

    def configure_values(self, values):
        self.values = values
        if self.dropdown_window:
            self.listbox.delete(0, "end")
            for val in values:
                self.listbox.insert("end", val)

# 取得程式資源路徑
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 顯示錯誤訊息
def show_error(title="錯誤", message="發生錯誤"):
    print(f"[ERROR] {title}: {message}")
    messagebox.showerror(title, message)

# 判斷 Minecraft 所需 Java 版本
def get_required_java_version(mc_version):
    try:
        print(mc_version)
        manifest = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json").json()
        # 只取 release 版本
        mc_cache = [v for v in manifest.get("versions", []) if v.get("type") == "release"]
        for v in mc_cache:
            if v.get("id") == mc_version and "url" in v:
                url = v["url"]
                print(url)
                ver_json = requests.get(url).json()
                if ver_json:
                    java_info = ver_json.get("javaVersion")
                    if java_info and "majorVersion" in java_info:
                        return int(java_info["majorVersion"])
    except Exception as e:
        show_error("Java版本判斷錯誤", str(e))

# 從 Adoptium API 取得 Java 下載連結
def get_adoptium_download_url(version):
    base = f"https://api.adoptium.net/v3/assets/latest/{version}/hotspot"
    params = {
        "architecture": "x64",
        "heap_size": "normal",
        "image_type": "jdk",
        "jvm_impl": "hotspot",
        "os": "windows",
        "vendor": "eclipse"
    }
    try:
        response = requests.get(base, params=params)
        response.raise_for_status()
        data = response.json()
        return data[0]["binary"]["package"]["link"]
    except Exception as e:
        show_error("Java下載失敗", f"取得下載網址時失敗：{e}")
        return None

# 自動下載 Java 並解壓縮、找出 java.exe
def download_java_with_progress(version, dest_folder, master, finish_callback):
    download_url = get_adoptium_download_url(version)
    if not download_url:
        finish_callback(None)
        return

    # 建立進度視窗
    progress_win = ctk.CTkToplevel(master)
    progress_win.configure(fg_color="#222222")
    progress_win.title("下載中...")
    progress_win.geometry("400x100")
    progress_win.resizable(False, False)
    progress_win.grab_set()

    label = ctk.CTkLabel(progress_win, text="正在下載 Java，請稍候...", font=("微軟正黑體", 14))
    label.pack(pady=(10, 10))

    progress_bar = ctk.CTkProgressBar(progress_win, width=350)
    progress_bar.pack(pady=(0, 10))
    progress_bar.set(0)

    temp_zip = os.path.join(tempfile.gettempdir(), f"java{version}.zip")

    def on_download_finish(java_path):
        progress_win.destroy()
        master.after(0, lambda: finish_callback(java_path))

    def download_task():
        java_path = None
        try:
            # 加入 retry 機制
            session = requests.Session()
            retries = requests.adapters.Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[502, 503, 504]
            )
            adapter = requests.adapters.HTTPAdapter(max_retries=retries)
            session.mount('https://', adapter)

            with session.get(download_url, stream=True) as r:
                r.raise_for_status()
                total_length = int(r.headers.get('content-length', 0))
                dl = 0
                start_time = time.time()
                last_update_time = time.time()

                with open(temp_zip, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=262144):  # 更大的 chunk
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)

                            # 節流進度條更新 (每0.05秒最多一次)
                            if total_length > 0:
                                now = time.time()
                                if now - last_update_time > 0.05:
                                    progress = dl / total_length
                                    progress_bar.set(progress)

                                    # 顯示速度（可省略）
                                    elapsed = now - start_time
                                    speed_kb = dl / 1024 / elapsed
                                    label.configure(text=f"正在下載 Java... {speed_kb:.1f} KB/s")
                                    last_update_time = now

            # 解壓縮
            extract_path = os.path.join(dest_folder, f"java{version}")
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            # 找到 java.exe 路徑
            for root, dirs, files in os.walk(extract_path):
                if "java.exe" in files:
                    java_path = os.path.join(root, "java.exe")
                    break

            if not java_path:
                show_error("Java未找到", "無法找到下載的 Java 執行檔")

        except Exception as e:
            show_error("Java下載失敗", f"錯誤: {e}")
            java_path = None
        finally:
            on_download_finish(java_path)

    threading.Thread(target=download_task, daemon=True).start()
# 取得可用的 Paper 版本列表
def get_paper_versions():
    try:
        response = requests.get("https://api.papermc.io/v2/projects/paper")
        response.raise_for_status()
        data = response.json()
        return data["versions"]
    except Exception as e:
        show_error("版本取得失敗", f"抓取版本資訊時發生錯誤：{e}")
        return []

# 寫入 eula.txt
def create_or_update_eula_file(agree: bool, folder_path: str):
    if not folder_path:
        return
    try:
        eula_path = os.path.join(folder_path, "eula.txt")
        with open(eula_path, "w", encoding="utf-8") as f:
            f.write(f"eula={'true' if agree else 'false'}\n")
    except Exception as e:
        show_error("EULA 檔案錯誤", f"寫入 EULA 檔案失敗：{e}")

# 建立 start.bat 啟動腳本
def create_start_bat(folder_path, min_memory, max_memory, use_gui, java_path=None):
    if not folder_path:
        show_error("安裝路徑錯誤", "請先選擇安裝路徑")
        return
    try:
        bat_path = os.path.join(folder_path, "start.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write(f'"{java_path if java_path else "java"}" -Xms{min_memory}M -Xmx{max_memory}M ')
            f.write("-Dnogui=false " if use_gui else "-Dnogui=true ")
            f.write("-jar server.jar\n" if use_gui else "-jar server.jar nogui\n")
            f.write("pause\n")
        print(f"成功建立 start.bat 檔案於 {bat_path}")
    except Exception as e:
        show_error("start.bat 錯誤", f"寫入 start.bat 失敗：{e}")

# 下載 Paper 伺服器 jar 檔
def DownloadServerJar(folder_path, version):
    if not folder_path or not version:
        show_error("下載失敗", "請先選擇安裝路徑和版本")
        return
    try:
        builds_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
        builds_response = requests.get(builds_url)
        builds_response.raise_for_status()
        builds_data = builds_response.json()
        latest_build = builds_data["builds"][-1]

        jar_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest_build}/downloads/paper-{version}-{latest_build}.jar"
        response = requests.get(jar_url)
        response.raise_for_status()

        jar_path = os.path.join(folder_path, "server.jar")
        with open(jar_path, "wb") as f:
            f.write(response.content)
        print(f"成功下載 {version} Build {latest_build} 的伺服器檔案至 {jar_path}")
    except Exception as e:
        show_error("下載錯誤", f"錯誤訊息：{e}")

# 建立 server.properties 設定檔
def create_server_properties(folder_path, online_mode, max_players, pvp, server_port):
    if not folder_path:
        return
    try:
        props_path = os.path.join(folder_path, "server.properties")
        with open(props_path, "w", encoding="utf-8") as f:
            f.write(f"online-mode={'true' if online_mode == '啟用' else 'false'}\n")
            f.write(f"max-players={max_players}\n")
            f.write(f"pvp={'true' if pvp == '啟用' else 'false'}\n")
            f.write(f"server-port={server_port}\n")
        print("server.properties 寫入完成")
    except Exception as e:
        show_error("server.properties 錯誤", f"寫入失敗：{e}")

# 開啟 EULA 網頁連結
def open_eula_link(event=None):
    webbrowser.open("https://account.mojang.com/documents/minecraft_eula")


# GUI 主體與元件建構
def CreateGUI():
    global version_dropdown, InstallPathEntry, eula_var, MinMemory_var, MaxMemory_var, ServerGUI_var, Download_Java_CheckBox_var
    global OnlineMode_ComboBox, MaxPlayers_var, PVP_ComboBox, port_var, status_var

    win = ctk.CTk()
    win.title("Minecraft 伺服器架設工具")
    win.geometry("550x580")
    win.resizable(False, False)

    icon_path = resource_path('GUI_icon.ico')
    try:
        win.iconbitmap(icon_path)
    except:
        pass

    tabview = ctk.CTkTabview(win)
    tabview.pack(expand=True, fill="both", padx=20, pady=20)
    tabview.add("基本設定")
    tabview.add("進階設定")
    tabview.add("關於我們")
    basic_tab = tabview.tab("基本設定")
    advanced_tab = tabview.tab("進階設定")
    about_tab = tabview.tab("關於我們")

    # 基本設定 Tab 元件
    label_version = ctk.CTkLabel(basic_tab, text="遊戲版本:", font=('微軟正黑體', 15, 'bold'))
    label_version.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="w")

    version_dropdown = ScrollableComboBox(basic_tab)
    version_dropdown.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="ew")
    versions = get_paper_versions()
    versions.reverse()
    version_dropdown.configure_values(versions)
    version_dropdown.set("請選擇版本")

    label_path = ctk.CTkLabel(basic_tab, text="安裝位置:", font=('微軟正黑體', 15, 'bold'))
    label_path.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")

    path_frame = ctk.CTkFrame(basic_tab)
    path_frame.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ew")
    path_frame.grid_columnconfigure(0, weight=1)

    InstallPathEntry = ctk.CTkEntry(path_frame, height=30, font=("微軟正黑體", 13))
    InstallPathEntry.grid(row=0, column=0, sticky="ew")

    def select_folder():
        folder = ctk.filedialog.askdirectory()
        if folder:
            InstallPathEntry.delete(0, "end")
            InstallPathEntry.insert(0, folder)

    btn_browse = ctk.CTkButton(path_frame, text="📁", width=30, command=select_folder, font=("微軟正黑體", 14, "bold"))
    btn_browse.grid(row=0, column=1)

    eula_var = tk.BooleanVar(value=False)
    label_eula = ctk.CTkLabel(basic_tab, text="EULA條款:", font=('微軟正黑體', 15, 'bold'))
    label_eula.grid(row=2, column=0, padx=(20, 10), pady=(10, 20), sticky="w")

    eula_checkbox = ctk.CTkCheckBox(basic_tab, text="我同意EULA條款", variable=eula_var, font=('微軟正黑體', 15, 'bold'))
    eula_checkbox.grid(row=2, column=1, padx=20, pady=(10, 20), sticky="w")

    eula_label = ctk.CTkLabel(basic_tab, text="查看EULA", text_color="yellow", font=("微軟正黑體", 13, "underline"), cursor="hand2")
    eula_label.grid(row=2, column=2, sticky="w", padx=(10, 10), pady=(10, 20))
    eula_label.bind("<Button-1>", open_eula_link)

    ServerGUI_var = tk.BooleanVar(value=False)
    ServerGUI_label = ctk.CTkLabel(basic_tab, text="GUI介面:", font=('微軟正黑體', 15, 'bold'))
    ServerGUI_label.grid(row=3, column=0, padx=(20, 10), pady=(10, 20), sticky="w")

    ServerGUI_checkbox = ctk.CTkCheckBox(basic_tab, text="啟用伺服器GUI介面", variable=ServerGUI_var, font=('微軟正黑體', 15, 'bold'))
    ServerGUI_checkbox.grid(row=3, column=1, padx=(20, 20), pady=(10, 20), sticky="w")

    Download_Java_CheckBox_var = tk.BooleanVar(value=False)
    Download_Java_CheckBox = ctk.CTkCheckBox(basic_tab, text="自動下載所需Java", variable=Download_Java_CheckBox_var, font=('微軟正黑體', 15, 'bold'))
    Download_Java_CheckBox.grid(row=4, column=1, padx=(20, 20), pady=(10, 20), sticky="w")

    MinMemory_var = tk.IntVar(value=1024)
    MaxMemory_var = tk.IntVar(value=4096)

    Memory_Label = ctk.CTkLabel(basic_tab, text="記憶體分配:", font=('微軟正黑體', 15, 'bold'), text_color="SkyBlue")
    Memory_Label.grid(row=5, column=0, padx=(20, 10), pady=(10, 20), sticky="w")

    MinMemory_Label = ctk.CTkLabel(basic_tab, text="最小記憶體 (MB):", font=('微軟正黑體', 13))
    MinMemory_Label.grid(row=6, column=0, padx=(20, 10), pady=(5, 5), sticky="w")
    MinMemory_Slider = ctk.CTkSlider(basic_tab, from_=1024, to=8192, variable=MinMemory_var, number_of_steps=16)
    MinMemory_Slider.grid(row=6, column=1, padx=(0, 20), pady=(5, 5), sticky="ew")

    MaxMemory_Label = ctk.CTkLabel(basic_tab, text="最大記憶體 (MB):", font=('微軟正黑體', 13))
    MaxMemory_Label.grid(row=7, column=0, padx=(20, 10), pady=(5, 20), sticky="w")
    MaxMemory_Slider = ctk.CTkSlider(basic_tab, from_=2048, to=8192, variable=MaxMemory_var, number_of_steps=32)
    MaxMemory_Slider.grid(row=7, column=1, padx=(0, 20), pady=(5, 20), sticky="ew")

    MinMemory_Display = tk.StringVar()
    MaxMemory_Display = tk.StringVar()

    def update_memory_display(*args):
        MinMemory_Display.set(f"{MinMemory_var.get()} MB")
        MaxMemory_Display.set(f"{MaxMemory_var.get()} MB")

    MinMemory_var.trace_add("write", update_memory_display)
    MaxMemory_var.trace_add("write", update_memory_display)
    update_memory_display()

    MinMemory_Text = ctk.CTkLabel(basic_tab, textvariable=MinMemory_Display, font=('微軟正黑體', 13))
    MinMemory_Text.grid(row=6, column=2, padx=(10, 20), pady=(5, 5), sticky="w")
    MaxMemory_Text = ctk.CTkLabel(basic_tab, textvariable=MaxMemory_Display, font=('微軟正黑體', 13))
    MaxMemory_Text.grid(row=7, column=2, padx=(10, 20), pady=(5, 20), sticky="w")

    # 狀態欄
    status_var = tk.StringVar(value="已就緒")
    StateText = ctk.CTkLabel(basic_tab, textvariable=status_var, font=('微軟正黑體', 17, 'bold'), text_color="#02F78E")
    StateText.grid(row=8, column=0, columnspan=3, padx=(20, 10), pady=(10, 20), sticky="w")

    # 進階設定 Tab 元件
    OnlineMode_var = tk.StringVar(value="啟用")
    OnlineMode_Label = ctk.CTkLabel(advanced_tab, text="正版驗證:\n(Online-Mode)", font=('微軟正黑體', 13, 'bold'), justify="left", anchor="w")
    OnlineMode_Label.grid(row=0, column=0, padx=(20, 10), pady=(10, 20), sticky="w")
    OnlineMode_ComboBox = ctk.CTkOptionMenu(advanced_tab, width=150, height=30, values=["啟用", "停用"], font=('微軟正黑體', 13))
    OnlineMode_ComboBox.grid(row=0, column=1, padx=(0, 20), pady=(10, 20), sticky="ew")
    OnlineMode_ComboBox.set("啟用")

    MaxPlayers_var = tk.IntVar(value=10)
    MaxPlayers_Label = ctk.CTkLabel(advanced_tab, text="玩家數量上限:\n(Max-Player)", font=('微軟正黑體', 13, 'bold'), justify="left", anchor="w")
    MaxPlayers_Label.grid(row=1, column=0, padx=(20, 10), pady=(10, 20), sticky="w")
    MaxPlayers_Entry = ctk.CTkEntry(advanced_tab, textvariable=MaxPlayers_var, width=100, height=30, font=("微軟正黑體", 13))
    MaxPlayers_Entry.grid(row=1, column=1, padx=(0, 20), pady=(10, 20), sticky="ew")

    PVP_var = tk.StringVar(value="啟用")
    PVP_label = ctk.CTkLabel(advanced_tab, text="玩家間傷害:\n(PVP)", font=('微軟正黑體', 13, 'bold'), justify="left", anchor="w")
    PVP_label.grid(row=3, column=0, padx=(20, 10), pady=(10, 20), sticky="w")
    PVP_ComboBox = ctk.CTkOptionMenu(advanced_tab, width=150, height=30, values=["啟用", "停用"], font=('微軟正黑體', 13))
    PVP_ComboBox.grid(row=3, column=1, padx=(0, 20), pady=(10, 20), sticky="ew")
    PVP_ComboBox.set("啟用")

    port_var = tk.IntVar(value=25565)
    Port_Label = ctk.CTkLabel(advanced_tab, text="伺服器連接埠:\n(Server Port)", font=('微軟正黑體', 13, 'bold'), justify="left", anchor="w")
    Port_Label.grid(row=4, column=0, padx=(20, 10), pady=(10, 20), sticky="w")
    Port_Entry = ctk.CTkEntry(advanced_tab, textvariable=port_var, width=100, height=30)
    Port_Entry.grid(row=4, column=1, padx=(0, 20), pady=(10, 20), sticky="ew")

    # 關於我們 Tab 元件 (表格版)
    about_label_title = ctk.CTkLabel(
        about_tab,
        text="Minecraft 伺服器架設工具",
        font=('微軟正黑體', 18, 'bold'),
        anchor="w"
    )
    about_label_title.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))

    about_label_version = ctk.CTkLabel(
        about_tab,
        text="版本：1.4",
        font=('微軟正黑體', 15),
        anchor="w"
    )
    about_label_version.grid(row=1, column=0, sticky="w", padx=20, pady=5)

    about_label_author = ctk.CTkLabel(
        about_tab,
        text="原作者：Evan小饅頭",
        font=('微軟正黑體', 15),
        anchor="w"
    )
    about_label_author.grid(row=2, column=0, sticky="w", padx=20, pady=5)

    # 分隔線
    separator = ctk.CTkFrame(about_tab, height=2, fg_color="#444444")
    separator.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 10))

    # 貢獻者名單標題
    about_label_contributors_title = ctk.CTkLabel(
        about_tab,
        text="貢獻者名單：",
        font=('微軟正黑體', 16, 'bold'),
        anchor="w"
    )
    about_label_contributors_title.grid(row=4, column=0, sticky="w", padx=20, pady=(5, 2))

    # 貢獻者列表 (名稱, 連結，如果沒有連結就 None)
    contributors = [
        ("Evan小饅頭", "https://www.youtube.com/channel/UCE8BD2BIgZIrdYl5l5niYHA/"),
        ("以下內容歡迎各位貢獻者加入！", None),
    ]

    # 顯示貢獻者
    for idx, (name, link) in enumerate(contributors, start=5):
        if link:  # 有連結 → 可點擊
            lbl = ctk.CTkLabel(
                about_tab,
                text=name,
                font=('微軟正黑體', 14, 'underline'),
                text_color="skyblue",
                cursor="hand2",
                anchor="w"
            )
            lbl.bind("<Button-1>", lambda e, url=link: webbrowser.open_new(url))
        else:  # 沒連結 → 純文字
            lbl = ctk.CTkLabel(
                about_tab,
                text=name,
                font=('微軟正黑體', 14),
                anchor="w"
            )
        lbl.grid(row=idx, column=0, sticky="w", padx=40, pady=2)

    # 開始佈署按鈕
    CreateServerButton = ctk.CTkButton(basic_tab, text='開始佈署', width=50, height=20, font=('微軟正黑體', 15, 'bold'))
    CreateServerButton.grid(row=8, column=2, columnspan=3, padx=(20, 20), pady=(5, 5), sticky="ew")

    return win, CreateServerButton, status_var
def on_create_server():
    # 先取得所有設定值
    folder = InstallPathEntry.get().strip()
    version = version_dropdown.get()
    agree_eula = eula_var.get()
    min_mem = MinMemory_var.get()
    max_mem = MaxMemory_var.get()
    use_gui = ServerGUI_var.get()

    online_mode = OnlineMode_ComboBox.get()
    max_players = MaxPlayers_var.get()
    pvp = PVP_ComboBox.get()
    server_port = port_var.get()

    # 檢查必填欄位
    if not folder:
        messagebox.showwarning("警告", "請選擇伺服器安裝路徑")
        return
    if version == "請選擇版本":
        messagebox.showwarning("警告", "請選擇遊戲版本")
        return
    if not agree_eula:
        messagebox.showwarning("警告", "請同意 EULA 條款")
        return
    if min_mem > max_mem:
        messagebox.showwarning("警告", "最小記憶體不得大於最大記憶體")
        return

    # 更新狀態欄
    status_var.set("開始架設伺服器中...")

    # 定義架設完成後的行為
    def setup_finished(success, msg=None):
        if success:
            status_var.set("伺服器架設完成！")
            messagebox.showinfo("成功", "伺服器設定完成！")
        else:
            status_var.set("伺服器架設失敗")
            if msg:
                messagebox.showerror("錯誤", msg)

    # 進行伺服器建立流程
    def continue_setup(java_path):
        try:
            create_start_bat(folder, min_mem, max_mem, use_gui, java_path)
            create_or_update_eula_file(agree_eula, folder)
            DownloadServerJar(folder, version)
            create_server_properties(folder, online_mode, max_players, pvp, server_port)
            setup_finished(True)
        except Exception as e:
            setup_finished(False, f"建立伺服器時發生錯誤：{e}")

    # 如果需要下載 Java，先下載 Java 再繼續架設
    if Download_Java_CheckBox_var.get():
        required_java = get_required_java_version(version)
        status_var.set(f"開始下載 Java {required_java}...")

        def on_java_download_finished(java_path):
            if java_path:
                status_var.set("Java 下載完成，繼續架設伺服器")
                continue_setup(java_path)
            else:
                status_var.set("Java 下載失敗")
                messagebox.showerror("錯誤", "Java 下載失敗，無法繼續架設")

        # 這邊呼叫你自訂的下載函式，需要支援 callback
        download_java_with_progress(required_java, folder, win, on_java_download_finished)

    else:
        # 不下載 Java，直接架設
        continue_setup(None)


# 最後，綁定開始佈署按鈕事件（假設你已經從 CreateGUI() 拿到按鈕）
win, CreateServerButton, status_var = CreateGUI()
CreateServerButton.configure(command=on_create_server)
win.mainloop()
