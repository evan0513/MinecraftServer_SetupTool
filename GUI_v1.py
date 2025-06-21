# import tkinter as tk
from tkinter import *
from tkinter import ttk

#安裝狀態
InstallState = False



win = Tk() #建立主視窗
win.title('Create Minecraft Server') #建立視窗標題


win.geometry('500x400') #設定視窗大小

# win.minsize(400, 200) #設定最小視窗大小

win.resizable(False, False) #設定視窗大小不可調整

#icon

win.iconbitmap('GUI_icon.ico') 

#顏色
win.config(bg='#323232')

#透明度
win.attributes('-alpha', 0.99) #透明度 0.0~1.0

#圖層置頂

win.attributes('-topmost', True) #置頂

#選取版本標籤
ChoseVersionText = Label()
ChoseVersionText.config(text='選取版本',fg='white',bg='#323232',font=('微軟正黑體', 15))
ChoseVersionText.place(x=20,y=10)
#安裝路徑標籤
InstallPathText = Label()
InstallPathText.config(text='安裝路徑',fg='white',bg='#323232',font=('微軟正黑體', 15))
InstallPathText.place(x=150,y=10)
#選取版本下拉選單
ChoseVersionCombobox = ttk.Combobox(win)
ChoseVersionCombobox.config(values=('Test'),width=10)
ChoseVersionCombobox.place(x=20,y=50)
ChoseVersionCombobox.current(0)

#顯示安裝路徑
ShowInstallPath = Entry(win)
ShowInstallPath.config(width=40,state='readonly')
ShowInstallPath.place(x=150,y=50)

#選取安裝路徑按鈕
SelectInstallPathButton = Button(win)
SelectInstallPathButton.config(text='📁',width=2,height=1,)
SelectInstallPathButton.place(x=450,y=50)

#正版驗證勾選框
OnlineModeCheckButton = Checkbutton(win)
OnlineModeCheckButton.config(text='正版驗證',fg='white',bg='#323232',font=('微軟正黑體', 15),selectcolor='#323232')
OnlineModeCheckButton.place(x=20,y=100)
#同意EULA勾選框
EULACheckButton = Checkbutton(win)
EULACheckButton.config(text='我同意EULA條款',fg='white',bg='#323232',font=('微軟正黑體', 13),selectcolor='#323232')
EULACheckButton.place(x=20,y=160)

#建立伺服器按鈕
CreateServerButton = Button(win)
CreateServerButton.config(text='建立伺服器',width=10,height=2,fg='white',bg='#323232',font=('微軟正黑體', 13))
CreateServerButton.place(x=330,y=130)
#測試用值
InstallState = True
#完成後顯示安裝成功字樣函式

def ChangeStateText():
    stateText.config(text='安裝成功!',fg='green',bg='#323232',font=('微軟正黑體', 20))
    stateText.place(x=20,y=250)

#請稍後字樣_完成後顯示安裝成功
stateText = Label()
stateText.config(text='請稍後...',fg='white',bg='#323232',font=('微軟正黑體', 20))
if InstallState == True:
    ChangeStateText()
    
stateText.place(x=20,y=250)
#常駐主視窗
win.mainloop() 