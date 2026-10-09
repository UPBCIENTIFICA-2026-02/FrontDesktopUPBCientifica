@echo off
rem ==========================================================================
rem  UPB-CIENTIFICA - Cliente de Escritorio
rem  Doble clic para abrir. La primera vez instala lo necesario.
rem ==========================================================================
setlocal
cd /d "%~dp0"
title UPB-CIENTIFICA

rem --- 1. Buscar Python -----------------------------------------------------
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo.
    echo  No se encontro Python en este equipo.
    echo  Instalalo desde https://www.python.org/downloads/
    echo  y marca la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

rem --- 2. Instalar dependencias solo si faltan ------------------------------
%PY% -c "import customtkinter, PIL" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias por primera vez, espera un momento...
    %PY% -m pip install --user -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  No se pudieron instalar las dependencias. Revisa tu conexion a internet.
        pause
        exit /b 1
    )
)

rem --- 3. Levantar el mock de autenticacion (si hay Node y no esta ya corriendo)
where node >nul 2>&1
if not errorlevel 1 (
    netstat -ano | findstr /R /C:":8080 .*LISTENING" >nul 2>&1
    if errorlevel 1 (
        start "Mock Auth UPB (no cerrar)" /min node "mock-auth-server\server.js"
    )
)

rem --- 4. Abrir la aplicacion sin dejar la consola abierta ------------------
set "PYW=pythonw"
where pyw >nul 2>&1 && set "PYW=pyw -3"
start "" %PYW% main.py
exit /b 0
