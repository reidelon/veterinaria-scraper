"""
utils.py — Shared utilities for hospital scraper.
"""

import sys
import threading


def ask_headless(timeout=5):
    """
    Ask the user whether to show the browser window.
    Waits up to `timeout` seconds for input; if none, defaults to headless.

    Returns True if headless, False if visible.
    """
    if not sys.stdin.isatty():
        print('\n[browser] Sin terminal interactiva → headless automático')
        return True

    print(f'\n¿Mostrar ventana del navegador? [s/N] (esperando {timeout}s, Enter o silencio = headless)... ',
          end='', flush=True)

    answer_holder = []
    def read_input():
        answer_holder.append(sys.stdin.readline().strip().lower())

    t = threading.Thread(target=read_input, daemon=True)
    t.start()
    t.join(timeout)

    if answer_holder:
        visible = answer_holder[0] in ('s', 'si', 'sí', 'y', 'yes')
    else:
        print('(sin respuesta)')
        visible = False

    mode = 'VISIBLE' if visible else 'HEADLESS'
    print(f'[browser] Modo: {mode}')
    return not visible  # returns True = headless
