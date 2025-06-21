# GUI_v3_Ctk.py GUI 程式碼，回傳 eula_var 給主程式
import customtkinter as ctk
import tkinter as tk
import os
import sys

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class ScrollableComboBox(ctk.CTkFrame):
    def __init__(self, master, width=150, height=30, dropdown_height=150, **kwargs):
        super().__init__(master, **kwargs)
        self.values = []
        self.var = tk.StringVar(value="")

        self.entry = ctk.CTkEntry(self, textvariable=self.var, width=width, height=height, state="readonly")
        self.entry.pack(fill="x")

        self.btn = ctk.CTkButton(self, text="▼", width=30, height=height, command=self.toggle_dropdown)
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

        self.listbox = tk.Listbox(self.dropdown_window, height=10)
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

def CreateGUI():
    InstallState = False

    win = ctk.CTk()
    win.title('Create Minecraft Server')
    win.geometry('500x400')
    win.resizable(False, False)

    icon_path = resource_path('GUI_icon.ico')
    try:
        win.iconbitmap(icon_path)
    except:
        pass

    ChoseVersionText = ctk.CTkLabel(win, text='選取版本', font=('微軟正黑體', 15, 'bold'))
    ChoseVersionText.place(x=20, y=10)

    InstallPathText = ctk.CTkLabel(win, text='安裝路徑', font=('微軟正黑體', 15, 'bold'))
    InstallPathText.place(x=150, y=10)

    ChoseVersionCombobox = ScrollableComboBox(win, width=120, height=30, dropdown_height=150)
    ChoseVersionCombobox.place(x=10, y=50)
    ChoseVersionCombobox.configure_values(['Test'])
    ChoseVersionCombobox.set("Test")

    ShowInstallPath = ctk.CTkEntry(win, width=250)
    ShowInstallPath.place(x=150, y=50)
    ShowInstallPath.configure(state="readonly")

    SelectInstallPathButton = ctk.CTkButton(win, text='📁', width=30, height=30)
    SelectInstallPathButton.place(x=410, y=50)

    eula_var = tk.BooleanVar(value=False)
    EULACheckButton = ctk.CTkCheckBox(win, text='我同意EULA條款', variable=eula_var,
                                      font=('微軟正黑體', 13, 'bold'))
    EULACheckButton.place(x=20, y=160)

    online_mode_var = tk.BooleanVar(value=True)  # 預設開啟正版驗證
    OnlineModeCheckButton = ctk.CTkCheckBox(win, text='正版驗證（online-mode）', font=('微軟正黑體', 15, 'bold'), variable=online_mode_var)
    OnlineModeCheckButton.place(x=20, y=100)

    CreateServerButton = ctk.CTkButton(win, text='建立伺服器', width=120, height=40,
                                       font=('微軟正黑體', 13, 'bold'))
    CreateServerButton.place(x=330, y=130)

    stateText = ctk.CTkLabel(win, text='請稍後...', font=('微軟正黑體', 20, 'bold'))
    stateText.place(x=20, y=250)
    if InstallState:
        stateText.configure(text='安裝成功!', text_color='green')

    CopyrightText = ctk.CTkLabel(win, text='Evan小饅頭製作 2025版權所有©', font=('微軟正黑體', 10, 'bold'))
    CopyrightText.place(x=20, y=370)

    progress = ctk.CTkProgressBar(win, width=400)
    progress.place(x=20, y=300)
    progress.set(0)

    return win, ChoseVersionCombobox, ShowInstallPath, SelectInstallPathButton, progress, CreateServerButton, stateText, InstallState, eula_var, online_mode_var
