# 開發者指南
這文件教你怎麼在電腦上建立執行環境、程式架構以及待新增的功能

您可以根據底下的功能或您的想法為本專案添磚加瓦！
## 建立執行環境
1. 下載並安裝Python
2. 使用Git clone下載本專案
3. 進入資料夾
4. 輸入以下指令建立虛擬環境
   ```shell
   Python -m venv venv
   ```
5. 激活虛擬環境
   ```shell
   .\venv\Scripts\activate.bat
   ```
6. 安裝第三方函示庫
   ```shell
   pip install -r requirements.txt
   ```
7. 執行程式 (完成)
   ```shell
   python .\src\ServerLauncher.py
   ```
## 打包
本專案目前使用 [Nuitka](https://nuitka.net/) 進行打包

## 專案架構
```txt
root
|--docs
|    |--...
|--src
|    |--Model
|    |    |--Downloader
|    |    |--Server
|    |    |--...
|    |--Windows
|    |    |--icon
|    |    |--...
|    |--...
|--...
```
`root` 項目根目錄
* `docs` 文件相關物品
* `src` 程式碼
  * `Model` 類別的實現項目，如Server, Java的下載、啟動等
    * `Downloader` Minecraft Server的下載，使用工廠模式以版本(Vanilla, Paper)進行分別
    * `Server` Minecraft Server的啟動項目，使用工廠模式以版本(Vanilla, Paper)進行分別，與Downloader進行關聯
  * `Windows` 視窗的交互程式碼
    * `icon` 程式會用到的icon

## 待新增的功能
* 全域設定
  - Java記憶體設定
  - 語言變更
  - 程式儲存資料夾變更
* 伺服器設定 (單伺服器的設定)
  - Java記憶體設定 (單Server)
  - 正版驗證開關
