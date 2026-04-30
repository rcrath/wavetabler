@echo off
REM Run via venv python directly so it works from any shell (cmd, bash, powershell)
"%~dp0wvtbl_win\Scripts\python.exe" "%~dp0src\a_wvtbl.py" %*
