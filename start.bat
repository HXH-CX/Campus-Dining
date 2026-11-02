@echo off
rem 校园食光 Windows 启动入口：双击或命令行 start.bat 都行
rem 真正的逻辑在 dev.py 里，两个平台共用一份，避免 .bat / .sh 各写一套再走岔
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 dev.py %*
) else (
    python dev.py %*
)

rem 双击运行时窗口会立刻关掉，暂停一下让人看清报错
if %errorlevel% neq 0 pause
