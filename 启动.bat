@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo   Weiless Prompt Studio
echo   ============================================
echo.

REM ---- 找 Python ----
REM 优先用 ComfyUI 整合包的 python_embeded：它已经装好 llama-cpp-python
REM 和 fastapi，不用另外 pip install 任何东西。
set "PY="

for %%P in (
  "G:\ComfyUI_Mie_V34\python_embeded\python.exe"
  "C:\Users\10030\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
) do (
  if exist %%P (
    if not defined PY set "PY=%%~P"
  )
)

if not defined PY (
  where python >nul 2>nul
  if !errorlevel! equ 0 set "PY=python"
)

if not defined PY (
  echo   [错误] 没找到 Python。
  echo   请编辑本文件顶部的路径列表，指向你的 python.exe。
  echo.
  pause
  exit /b 1
)

echo   解释器: %PY%
echo.

REM ---- 检查依赖 ----
"%PY%" -c "import fastapi, uvicorn, llama_cpp" >nul 2>nul
if !errorlevel! neq 0 (
  echo   [错误] 这个 Python 缺少依赖。装一下：
  echo.
  echo     "%PY%" -m pip install fastapi uvicorn llama-cpp-python
  echo.
  pause
  exit /b 1
)

REM ---- 外挂风格库没导入过就提示 ----
if not exist "catalog\local_styles.json" (
  echo   [提示] 外挂风格库还没导入，工具只有内置的 198 条风格。
  echo          想用上本机 ComfyUI 里的 3000+ 条风格，跑一次：
  echo.
  echo             "%PY%" tools\import_local_styles.py
  echo.
)

echo   启动中…浏览器会自动打开
echo   关掉这个窗口即停止服务
echo.

"%PY%" app.py --open

pause
