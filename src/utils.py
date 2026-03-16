"""
utils.py — Shared utilities for hospital scraper.
"""

import select
import sys


def ask_headless(timeout=5):
    """
    Ask the user whether to show the browser window.
    Waits up to `timeout` seconds for input; if none, defaults to headless.

    Returns True if headless, False if visible.
    """
    # If not a real terminal (e.g. piped), default to headless
    if not sys.stdin.isatty():
        print('\n[browser] Sin terminal interactiva → headless automático')
        return True

    print(f'\n¿Mostrar ventana del navegador? [s/N] (esperando {timeout}s, Enter o silencio = headless)... ',
          end='', flush=True)

    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        answer = sys.stdin.readline().strip().lower()
        visible = answer in ('s', 'si', 'sí', 'y', 'yes')
    else:
        print('(sin respuesta)')
        visible = False

    mode = 'VISIBLE' if visible else 'HEADLESS'
    print(f'[browser] Modo: {mode}')
    return not visible  # returns True = headless
