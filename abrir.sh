#!/usr/bin/env bash
# UPB-CIENTÍFICA — Cliente de Escritorio (Linux). Ejecuta: ./abrir.sh
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo "No se encontró python3. Instálalo con: sudo apt install python3 python3-tk python3-pip"
    exit 1
fi

if ! python3 -c "import customtkinter, PIL" >/dev/null 2>&1; then
    echo "Instalando dependencias por primera vez..."
    python3 -m pip install --user -r requirements.txt || exit 1
fi

# Mock de autenticación, si hay Node y el puerto 8080 está libre
if command -v node >/dev/null 2>&1 && ! (echo > /dev/tcp/127.0.0.1/8080) >/dev/null 2>&1; then
    nohup node mock-auth-server/server.js >/dev/null 2>&1 &
fi

nohup python3 main.py >/dev/null 2>&1 &
