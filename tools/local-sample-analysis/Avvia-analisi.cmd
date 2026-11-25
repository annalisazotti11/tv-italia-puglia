@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto fallback
py -3.12 -V >nul 2>nul
if errorlevel 1 goto fallback
py -3.12 "%~dp0avvia.py"
goto done
:fallback
where python >nul 2>nul
if errorlevel 1 goto missing
python "%~dp0avvia.py"
goto done
:missing
echo Installa Python dalla pagina ufficiale: https://www.python.org/downloads/windows/
:done
pause
endlocal
