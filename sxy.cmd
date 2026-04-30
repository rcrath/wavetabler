@echo off
setlocal enabledelayedexpansion

set "FOLDER=wavetables"
if not exist "%FOLDER%" (
    echo Folder "%FOLDER%" not found.
    exit /b 1
)

echo.
echo Wavetables in %FOLDER%:
echo.
set count=0
for %%f in ("%FOLDER%\*.wav") do (
    set /a count+=1
    set "file[!count!]=%%~nxf"
    echo   !count!: %%~nxf
)

if %count% equ 0 (
    echo   ^(no .wav files found^)
    exit /b 1
)

echo.
set /p "choice=Select a file by number (or q to quit): "

if /i "%choice%"=="q" exit /b 0
if not defined file[%choice%] (
    echo Invalid selection.
    exit /b 1
)

echo.
echo === !file[%choice%]! ===
sox --i "%FOLDER%\!file[%choice%]!"
echo.
endlocal
