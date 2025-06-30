@echo off
REM ---- Nuitka 單一檔案打包腳本 ----

set MAINFILE=src/ServerLauncher.py
set ICON=logo.ico
set OUTDIR=dist

set CTKMSGBOX_ICONS=venv/Lib/site-packages/CTkMessagebox/icons/*


nuitka ^
    --standalone ^
    --enable-plugin=tk-inter ^
    --windows-icon-from-ico=%ICON% ^
    --windows-disable-console ^
    --onefile ^
    --include-data-files="src/Windows/icon/*=Windows/icon/" ^
    --include-data-files="%CTKMSGBOX_ICONS%=CTkMessagebox/icons/" ^
    --output-dir=%OUTDIR% ^
    %MAINFILE%