# main.py

import os
import requests
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
from GUI.GUI_v3_Ctk import CreateGUI


# 建立 GUI，會回傳 eula_var
win, ChoseVersionCombobox, ShowInstallPath, SelectInstallPathButton, progress, CreateServerButton, stateText, InstallState, eula_var, online_mode_var, maximux_memory = CreateGUI()


# 取得 PaperMC 版本列表，並更新下拉選單
def fetch_versions():
    try:
        response = requests.get("https://api.papermc.io/v2/projects/paper")
        response.raise_for_status()
        data = response.json()
        versions = data["versions"]
        versions.reverse()
        ChoseVersionCombobox.configure_values(versions)
        ChoseVersionCombobox.set(versions[0])
    except Exception as e:
        messagebox.showerror("錯誤", f"無法獲取版本列表：\n{e}")

fetch_versions()


# 選擇安裝路徑
def select_install_path():
    path = filedialog.askdirectory(title="選擇安裝資料夾")
    if path:
        ShowInstallPath.configure(state='normal')
        ShowInstallPath.delete(0, 'end')
        ShowInstallPath.insert(0, path)
        ShowInstallPath.configure(state='readonly')

SelectInstallPathButton.configure(command=select_install_path)


# 取得指定版本最新build號
def get_latest_build(version):
    try:
        url = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        latest_build = data['builds'][-1]
        return latest_build
    except Exception as e:
        messagebox.showerror("錯誤", f"無法取得 build 資訊：\n{e}")
        return None


# 建立 eula.txt 與啟動 bat 檔
def create_startup_files(install_path, jar_file):
    # 建立 eula.txt
    eula_path = os.path.join(install_path, "eula.txt")
    with open(eula_path, "w", encoding="utf-8") as f:
        f.write("eula=true\n")

    # 建立 server.properties 並設定 online-mode
    server_properties_path = os.path.join(install_path, "server.properties")
    online_mode = "true" if online_mode_var.get() else "false"
    with open(server_properties_path, "w", encoding="utf-8") as f:
        f.write(f"online-mode={online_mode}\n")

    # 建立啟動 bat 檔
    jar_full_path = os.path.join(install_path, jar_file)
    bat_content = f"""@echo off
java -Xmx{int((maximux_memory.get()//512)*512)}M -Xms1024M -jar "{jar_full_path}"
pause
"""
    bat_path = os.path.join(install_path, "啟動伺服器.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    def show_info():
        messagebox.showinfo("完成","伺服器啟動檔已建立!\n請使用啟動伺服器.bat來啟動伺服器。")
        os.startfile(install_path)
    win.after(0, show_info)
#------------------------------------------------------------------------#
# 在下載完成後編輯 server.properties

def edit_server_properties(install_path, online_mode=True):
    prop_path = os.path.join(install_path, "server.properties")
    if not os.path.exists(prop_path):
        return  # server.properties 尚未生成，先不處理

    with open(prop_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    with open(prop_path, 'w', encoding='utf-8') as f:
        found = False
        for line in lines:
            if line.strip().startswith("online-mode="):
                f.write(f"online-mode={'true' if online_mode else 'false'}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"\nonline-mode={'true' if online_mode else 'false'}\n")

#-------------------------------------------------------------------------#

def check_dir_clear(download_path):
    p = os.listdir(download_path)
    return not p

# 下載伺服器檔案
def download_server_file(version, download_path):
    try:
        if not check_dir_clear(download_path):
            raise BaseException("目標資料夾不為空")
        build = get_latest_build(version)
        if build is None:
            return

        url = f'https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar'
        stateText.configure(text="正在下載伺服器檔案...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        file_name = url.split("/")[-1]
        file_path = os.path.join(download_path, file_name)
        total_size = int(response.headers.get('content-length', 0))

        chunk_size = 65536  # 64KB
        downloaded = 0

        with open(file_path, 'wb') as f:
            progress.set(0)
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        progress.set(downloaded / total_size)
                    win.update_idletasks()

            progress.set(1.0)
            win.update_idletasks()

        messagebox.showinfo("成功", "伺服器檔案已下載完畢！")
        stateText.configure(text="下載完成！")
        create_startup_files(download_path, file_name)
        edit_server_properties(download_path, online_mode=online_mode_var.get())
        return file_path

    except requests.exceptions.RequestException as e:
        messagebox.showerror("錯誤", f"下載過程中出現錯誤：{e}")
        stateText.configure(text="下載失敗！")
        return None
    
    except BaseException as e:
        messagebox.showerror("錯誤", f"下載過程中出現錯誤：{e}")
        stateText.configure(text="資料夾不為空!")
        return None


# 主下載函式，先判斷 EULA 是否勾選
def download_server():
    if not eula_var.get():
        messagebox.showerror("錯誤", "請先同意 EULA 條款才能繼續！")
        return

    selected_version = ChoseVersionCombobox.get()
    if not selected_version or selected_version == 'Test':
        messagebox.showerror("錯誤", "請選擇正確的版本！")
        return

    install_path = ShowInstallPath.get()
    if not install_path:
        messagebox.showerror("錯誤", "請選擇安裝路徑！")
        return

    # 子執行緒執行下載避免卡住UI
    threading.Thread(target=download_server_file, args=(selected_version, install_path), daemon=True).start()

if __name__ == "__main__":
    CreateServerButton.configure(command=download_server)
    win.mainloop()
