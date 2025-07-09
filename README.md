# Minecraft 伺服器安裝程式

一個現代化的多語言 GUI 應用程式，用於安裝和管理支援多種伺服器核心的 Minecraft 伺服器。

## 功能特色

### 🌍 多語言支援
- 英語、中文（簡體/繁體）、西班牙語、法語
- 即時語言切換
- 本地化安裝訊息

### 🎨 現代化介面
- 深色、淺色和系統主題
- 基於 CustomTkinter 的現代化 GUI
- 直觀的使用者體驗

### 🔧 伺服器核心支援
- **Vanilla** - 官方 Minecraft 伺服器
- **Paper** - 高效能插件支援伺服器
- **Spigot** - 熱門插件支援伺服器
- **Forge** - 模組伺服器支援
- **Fabric** - 輕量化模組伺服器

### 📦 安裝功能
- 自動版本偵測和選擇
- 一鍵伺服器安裝
- 自動 EULA 接受
- 跨平台啟動腳本生成
- 本地化進度追蹤訊息

### 🛠️ 伺服器管理
- 基於專案的伺服器管理
- 伺服器屬性編輯器
- 模組/插件管理
- 世界管理和備份
- 玩家管理（管理員、白名單、封禁）
- 即時伺服器控制台
- 伺服器啟動/停止/重啟控制

## 安裝方式

### 系統需求
- Python 3.7+
- 必要套件（透過 pip 安裝）：

```bash
pip install -r requirements.txt
```

### 依賴套件
- `customtkinter` - 現代化 GUI 框架
- `requests` - HTTP 請求處理
- `packaging` - 版本解析

## 使用方式

1. **執行應用程式：**
```bash
python main.py
```

2. **建立新伺服器：**
   - 選擇安裝目錄
   - 選擇伺服器核心（Vanilla、Paper、Spigot、Forge、Fabric）
   - 選擇 Minecraft 版本
   - 接受 EULA
   - 點擊「安裝伺服器」

3. **管理現有伺服器：**
   - 使用「開啟伺服器專案」來管理現有伺服器
   - 編輯伺服器屬性
   - 管理模組/插件
   - 控制伺服器操作

## 設定配置

設定會自動儲存到您的使用者目錄：
- **Windows：** `%USERPROFILE%\.minecraft_server_installer\config.json`
- **Linux/Mac：** `~/.minecraft_server_installer/config.json`

## 支援的伺服器版本

- **Vanilla：** 所有官方 Minecraft 版本（正式版 + 快照版）
- **Paper：** 最新 50 個版本，具即時 API 整合
- **Spigot：** 主要發布版本
- **Forge：** 支援 Forge 的版本
- **Fabric：** 所有支援的 Minecraft 版本

## 檔案結構

```
MinecraftServerInstaller/
├── main.py              # 主要應用程式
├── translations.py      # 多語言支援
├── config.py           # 配置管理
├── requirements.txt    # 依賴套件
├── README.md          # 此檔案
└── CLAUDE.md          # 開發備註
```

## 貢獻方式

1. Fork 此儲存庫
2. 建立功能分支
3. 進行您的變更
4. 徹底測試
5. 提交 pull request

## 授權條款

此專案為開源專案。使用此軟體時請確保遵守 Minecraft 的 EULA。

## 螢幕截圖

應用程式特色：
- 現代化深色/淺色主題介面
- 多語言支援
- 伺服器管理控制台
- 版本選擇與搜尋過濾
- 即時伺服器監控

## 開發資訊

使用技術：
- **Python 3.7+**
- **CustomTkinter** 現代化 GUI
- **Requests** API 整合
- **Threading** 非阻塞操作
- **JSON** 配置管理

## 技術支援

如有問題或功能請求，請在儲存庫中建立 issue。

## 作者

由 Dennis911 開發

---

**注意：** 此軟體與 Mojang Studios 或 Microsoft 無關。Minecraft 是 Mojang Studios 的商標。