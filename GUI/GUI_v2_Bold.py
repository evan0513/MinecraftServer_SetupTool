from tkinter import *
from tkinter import ttk
import os
import sys  # 這行新增

# 加這個函數來確保打包後能正確讀取圖示
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def CreateGUI():
    InstallState = False

    win = Tk()
    win.title('Create Minecraft Server')
    win.geometry('500x400')
    win.resizable(False, False)
    
    # 改成用 resource_path 尋找圖示
    icon_path = resource_path('GUI_icon.ico')
    win.iconbitmap(icon_path)
    win.config(bg='#323232')
    win.attributes('-alpha', 0.99)
    win.attributes('-topmost', True)

    # 選取版本標籤
    ChoseVersionText = Label(win, text='選取版本', fg='white', bg='#323232', font=('微軟正黑體', 15, 'bold'))
    ChoseVersionText.place(x=20, y=10)

    # 安裝路徑標籤
    InstallPathText = Label(win, text='安裝路徑', fg='white', bg='#323232', font=('微軟正黑體', 15, 'bold'))
    InstallPathText.place(x=150, y=10)

    # 選取版本下拉選單
    ChoseVersionCombobox = ttk.Combobox(win, values=('Test',), width=10)
    ChoseVersionCombobox.place(x=20, y=50)
    ChoseVersionCombobox.current(0)

    # 顯示安裝路徑
    ShowInstallPath = Entry(win, width=40, state='readonly')
    ShowInstallPath.place(x=150, y=50)

    # 選取安裝路徑按鈕
    SelectInstallPathButton = Button(win, text='📁', width=2, height=1)
    SelectInstallPathButton.place(x=450, y=50)

    # 正版驗證勾選框
    OnlineModeCheckButton = Checkbutton(win, text='正版驗證(此功能尚在開發)', fg='white', bg='#323232',
                                        font=('微軟正黑體', 15, 'bold'), selectcolor='#323232')
    OnlineModeCheckButton.place(x=20, y=100)

    # 同意EULA勾選框
    EULACheckButton = Checkbutton(win, text='我同意EULA條款(此功能尚在開發)', fg='white', bg='#323232',
                                  font=('微軟正黑體', 13, 'bold'), selectcolor='#323232')
    EULACheckButton.place(x=20, y=160)

    # 建立伺服器按鈕
    CreateServerButton = Button(win, text='建立伺服器', width=10, height=2,
                                fg='white', bg='#323232', font=('微軟正黑體', 13, 'bold'))
    CreateServerButton.place(x=330, y=130)

    # 安裝狀態文字
    stateText = Label(win, text='請稍後...', fg='white', bg='#323232', font=('微軟正黑體', 20, 'bold'))
    stateText.place(x=20, y=250)

    if InstallState:
        stateText.config(text='安裝成功!', fg='green')

    # 版權文字
    CopyrightText = Label(win, text='Evan小饅頭製作 2025版權所有©',
                          fg='white', bg='#323232', font=('微軟正黑體', 10, 'bold'))
    CopyrightText.place(x=20, y=370)

    # 創建進度條
    progress = ttk.Progressbar(win, length=400, mode='determinate')
    progress.place(x=20, y=300)


    # 回傳需要操作的元件（例如版本選單、安裝路徑框、選擇路徑按鈕、進度條）
    return win, ChoseVersionCombobox , ShowInstallPath, SelectInstallPathButton, progress , CreateServerButton, stateText, InstallState
