#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UPB-CIENTÍFICA — Cliente de Escritorio (Windows / Linux)
Punto de entrada. Ejecuta:  python main.py

Modos de prueba:
  python main.py --smoke            # recorre las vistas y cierra (test headless)
  python main.py --stay view=album  # abre una vista y no cierra (para capturas)
"""

import sys

from app.app import UPBApp


def main():
    app = UPBApp()
    if "--smoke" in sys.argv:
        def _smoke():
            app.enter_main()
            for key, _ in app.NAV:
                app.show_view(key)
            app.after(300, app.destroy)
        app.after(300, _smoke)
    elif "--stay" in sys.argv:
        view = "dashboard"
        for a in sys.argv:
            if a.startswith("view="):
                view = a.split("=", 1)[1]
        def _stay():
            app.enter_main()
            app.show_view(view)
        app.after(300, _stay)
    app.mainloop()


if __name__ == "__main__":
    main()
