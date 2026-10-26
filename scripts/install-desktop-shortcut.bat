@echo off
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "DEST=%~1"
if "%DEST%"=="" for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DEST=%%D"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%DEST%\Tasjeel.lnk');" ^
  "$s.TargetPath = '%ROOT%\scripts\launch-tasjeel.bat';" ^
  "$s.WorkingDirectory = '%ROOT%';" ^
  "$s.IconLocation = '%ROOT%\src\tasjeel\resources\tasjeel.ico,0';" ^
  "$s.WindowStyle = 7;" ^
  "$s.Description = 'Launch Tasjeel';" ^
  "$s.Save()"
if errorlevel 1 (
    echo Could not create the shortcut.
    pause
    exit /b 1
)
echo Created "%DEST%\Tasjeel.lnk"
