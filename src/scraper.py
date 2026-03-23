"""
scraper.py — Main loop for hospital clinical records scraper.
Processes cases 0001/2023 → 3279/2023, downloads PDFs and writes to CSV.
"""

import csv
import os
import sys
import time
import signal
import shutil
from datetime import datetime
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.config import (
    LOGIN_URL, MASCOTAS_URL, USERNAME, PASSWORD,
    START_CASE, END_CASE, YEAR,
    DOWNLOAD_DIR, OUTPUT_DIR,
    MISSING_CASES_FILE, ERRORS_FILE,
    SLEEP_MEDIUM, SLEEP_SHORT,
)
from navigator import (
    login, ensure_session,
    search_case, get_pet_row, get_ficha_buttons, download_ficha,
    _click, _wait_mask_gone,
)
from pdf_extractor import extract_fields, is_data_complete
from csv_writer import init_csv, write_row, get_processed_cases
from utils import ask_headless

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

is_shutting_down = False
DOWNLOAD_DIR_ABS = os.path.abspath(DOWNLOAD_DIR)


def signal_handler(signum, frame):
    global is_shutting_down
    if is_shutting_down:
        print('\n[scraper] Forzando salida...')
        sys.exit(1)
    print('\n[scraper] Ctrl+C recibido, terminando al finalizar el caso actual... (Ctrl+C de nuevo para salida inmediata)')
    is_shutting_down = True

signal.signal(signal.SIGINT, signal_handler)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_driver(headless):
    opts = webdriver.ChromeOptions()
    prefs = {
        'download.default_directory': DOWNLOAD_DIR_ABS,
        'download.prompt_for_download': False,
        'plugins.always_open_pdf_externally': True,
    }
    opts.add_experimental_option('prefs', prefs)
    opts.add_experimental_option('excludeSwitches', ['enable-logging'])
    opts.add_argument('--ignore-certificate-errors')
    opts.add_argument('--ignore-ssl-errors')
    if headless:
        opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=opts)


_ERRORS_COLUMNS = ['Fecha y hora', 'Nro Ficha', 'Motivo', 'Link para revisar manualmente']
_LINK = f'http://164.73.21.67:8080/hospital7.0d/com.hospital.arranque'

_REASON_MAP = {
    'no results':                    'La ficha no fue encontrada en el sistema',
    'grid not found':                'La ficha no fue encontrada en el sistema',
    'get_pet_row failed':            'No se pudo identificar la mascota dentro de la ficha del propietario',
    'no print buttons in wwfichas':  'La ficha existe pero no tiene consultas registradas para imprimir',
    'no fields extracted':           'Se descargó el PDF pero no se pudo leer la información',
}


def _human_reason(technical_reason):
    for key, human in _REASON_MAP.items():
        if key in technical_reason:
            return human
    if 'download timeout' in technical_reason:
        return 'No se pudo descargar el PDF de la ficha (tiempo de espera agotado)'
    return f'Error inesperado al procesar la ficha: {technical_reason}'


def _init_errors_csv():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(ERRORS_FILE):
        with open(ERRORS_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            csv.DictWriter(f, fieldnames=_ERRORS_COLUMNS).writeheader()


def log_missing(case_number):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(MISSING_CASES_FILE, 'a', encoding='utf-8') as f:
        f.write(case_number + '\n')
    _write_error_row(case_number, 'La ficha no fue encontrada en el sistema')


def log_error(case_number, reason):
    _write_error_row(case_number, _human_reason(reason))


def _write_error_row(case_number, human_reason):
    _init_errors_csv()
    row = {
        'Fecha y hora':             datetime.now().strftime('%d/%m/%Y %H:%M'),
        'Nro Ficha':                case_number,
        'Motivo':                   human_reason,
        'Link para revisar manualmente': _LINK,
    }
    with open(ERRORS_FILE, 'a', newline='', encoding='utf-8-sig') as f:
        csv.DictWriter(f, fieldnames=_ERRORS_COLUMNS).writerow(row)


def read_missing_cases():
    if not os.path.exists(MISSING_CASES_FILE):
        return set()
    with open(MISSING_CASES_FILE, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}


def rename_pdf(src, case_number):
    """Rename aimpresionuno_impl.pdf → NNNN_YYYY.pdf"""
    safe = case_number.replace('/', '_')
    dst = os.path.join(DOWNLOAD_DIR_ABS, f'{safe}.pdf')
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)
    return dst


def navigate_to_fichas(driver, case_number):
    """
    From todasmascotas search result, navigate all the way to wwfichas.
    Returns list of print button IDs (oldest first), or None on failure.
    """
    result = search_case(driver, case_number)
    if result is None:
        return None, None   # case not found

    especie = result['especie']
    if especie not in ('CANINO', 'FELINO'):
        return especie, []  # skip silently

    # Click cedula → wwclientes
    _click(driver, result['cedula_link'])
    time.sleep(SLEEP_MEDIUM)

    # Click mostrar mascotas → wwmascotas
    btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'vBOTONMASCOTA_0001'))
    )
    _click(driver, btn)

    # Find the correct pet row
    row = get_pet_row(driver, case_number)
    if row is None:
        return especie, None

    # Click ir a fichas → wwfichas
    row_id = str(row).zfill(4)
    ficha_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, f'vBOTONFICHA_{row_id}'))
    )
    _click(driver, ficha_btn)
    time.sleep(SLEEP_MEDIUM)

    btns = get_ficha_buttons(driver)
    return especie, btns


def process_case(driver, case_number):
    """
    Full processing for one case number.
    Returns True on success, False on error, None if skipped.
    """
    try:
        especie, btns = navigate_to_fichas(driver, case_number)

        # Case not found in system
        if btns is None and especie is None:
            log_missing(case_number)
            print(f'[{case_number}] No encontrado → missing_cases.txt')
            return None

        # Not canino/felino — skip silently
        if btns == []:
            print(f'[{case_number}] Especie={especie}, saltando')
            return None

        # Navigation failed after finding the case
        if btns is None:
            log_error(case_number, 'get_pet_row failed')
            return False

        if not btns:
            log_error(case_number, 'no print buttons in wwfichas')
            return False

        # Download PDFs, try oldest first, fallback to newer if data incomplete
        # Note: clicking the print button does NOT navigate away from wwfichas,
        # so we stay on the page and can click the next button directly.
        fields = None
        downloaded_pdfs = []
        for btn_id in btns:
            pdf_tmp = download_ficha(driver, btn_id, DOWNLOAD_DIR_ABS)
            if not pdf_tmp:
                # Reintento único antes de pasar al siguiente botón
                print(f'[{case_number}] Reintentando {btn_id}...')
                time.sleep(SLEEP_MEDIUM)
                pdf_tmp = download_ficha(driver, btn_id, DOWNLOAD_DIR_ABS)
            if not pdf_tmp:
                continue

            pdf_path = rename_pdf(pdf_tmp, case_number)
            downloaded_pdfs.append(pdf_path)
            current = extract_fields(pdf_path)

            if fields is None:
                fields = current
            else:
                # Fill in missing motivo/examen from newer consultations
                if not fields.get('motivo_consulta') and current.get('motivo_consulta'):
                    fields['motivo_consulta'] = current['motivo_consulta']
                if not fields.get('examen_objetivo') and current.get('examen_objetivo'):
                    fields['examen_objetivo'] = current['examen_objetivo']

            if is_data_complete(fields):
                break

        if fields is None:
            log_error(case_number, 'No se pudo descargar ningún PDF de la ficha')
            return False

        write_row(fields, case_number)
        for pdf in downloaded_pdfs:
            try:
                os.remove(pdf)
            except OSError:
                pass
        print(f'[{case_number}] OK — {especie} {fields.get("raza")} '
              f'| {fields.get("especialidad")} | paraje={fields.get("paraje")}')
        return True

    except Exception as e:
        log_error(case_number, str(e))
        print(f'[{case_number}] ERROR: {e}')
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args():
    """
    Usage: python scraper.py [N]
      N  — optional, number of cases to process (default: all until END_CASE)
    """
    import argparse
    parser = argparse.ArgumentParser(description='Hospital scraper')
    parser.add_argument('limit', nargs='?', type=int, default=None,
                        help='Número de casos a procesar (ej: 10). Sin valor = todos.')
    return parser.parse_args()


def _fmt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f'{h}h {m}m {s}s'
    elif m:
        return f'{m}m {s}s'
    return f'{s}s'


def main():
    global is_shutting_down

    args = _parse_args()
    headless = ask_headless(timeout=5)

    os.makedirs(DOWNLOAD_DIR_ABS, exist_ok=True)
    init_csv()

    already_done = get_processed_cases()
    already_done |= read_missing_cases()
    print(f'[scraper] Casos ya procesados/missing: {len(already_done)}')

    # Determine range
    end = START_CASE + args.limit - 1 if args.limit else END_CASE
    total_to_process = end - START_CASE + 1
    print(f'[scraper] Rango: {START_CASE:04d}/{YEAR} → {end:04d}/{YEAR} ({total_to_process} casos)')

    driver = setup_driver(headless)
    t_start = time.time()

    try:
        if not login(driver):
            print('[scraper] Login fallido, abortando.')
            return

        stats = {'ok': 0, 'skip': 0, 'error': 0}
        processed_this_run = 0

        bar = tqdm(
            range(START_CASE, end + 1),
            total=total_to_process,
            unit='caso',
            dynamic_ncols=True,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}'
        )
        # Redirect print so logs don't break the bar
        import builtins
        _orig_print = builtins.print
        builtins.print = lambda *a, **kw: tqdm.write(' '.join(str(x) for x in a))

        for i in bar:
            if is_shutting_down:
                bar.write('[scraper] Apagado solicitado, saliendo...')
                break

            case = f'{i:04d}/{YEAR}'

            if case in already_done:
                bar.update(0)
                continue

            # Ensure we're on todasmascotas before each case
            if 'todasmascotas' not in driver.current_url:
                ensure_session(driver)
                driver.get(MASCOTAS_URL)
                time.sleep(SLEEP_MEDIUM)

            result = process_case(driver, case)
            processed_this_run += 1

            if result is True:
                stats['ok'] += 1
                already_done.add(case)
            elif result is False:
                stats['error'] += 1
            else:
                already_done.add(case)
                stats['skip'] += 1

            bar.set_postfix(ok=stats['ok'], skip=stats['skip'], err=stats['error'], refresh=True)

            # Check session every 50 cases
            if processed_this_run % 50 == 0:
                ensure_session(driver)

        elapsed = time.time() - t_start
        builtins.print = _orig_print
        print(f'\n[scraper] Terminado en {_fmt_time(elapsed)}')
        print(f'  ok={stats["ok"]} | skip={stats["skip"]} | errores={stats["error"]}')

    finally:
        driver.quit()


if __name__ == '__main__':
    main()
