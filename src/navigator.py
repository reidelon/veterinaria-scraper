"""
navigator.py — Selenium navigation module for hospital scraper.
All browser interactions with the hospital web app are encapsulated here.
"""

import os
import re
import time
import sys

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.config import (
    LOGIN_URL, MASCOTAS_URL, USERNAME, PASSWORD,
    WAIT_TIMEOUT, SLEEP_SHORT, SLEEP_MEDIUM, SLEEP_LONG,
    DOWNLOAD_TIMEOUT,
)

SPECIES_VALID = {'CANINO', 'FELINO', 'FELINA'}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _wait(driver, by, value, timeout=None, clickable=False):
    """Return element once present (and optionally clickable), or None."""
    t = timeout or WAIT_TIMEOUT
    try:
        condition = EC.element_to_be_clickable((by, value)) if clickable \
            else EC.presence_of_element_located((by, value))
        return WebDriverWait(driver, t).until(condition)
    except TimeoutException:
        return None


def _wait_mask_gone(driver, timeout=10):
    """Wait until the GeneXus loading mask (gx-mask) disappears."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.gx-mask'))
        )
    except TimeoutException:
        pass


def _click(driver, element):
    """Wait for mask, then JS click with fallback to regular click."""
    _wait_mask_gone(driver)
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        driver.execute_script("arguments[0].click();", element)
    except Exception:
        element.click()


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def is_session_alive(driver):
    """Return True if we are NOT on the login or arranque page."""
    url = driver.current_url
    return 'login' not in url and 'arranque' not in url


def login(driver):
    """
    Full login flow: arranque → click Hospital → fill credentials → submit.
    Returns True on success.
    """
    driver.get(LOGIN_URL)
    time.sleep(SLEEP_SHORT)

    # If redirected to arranque, click the Hospital image first
    if 'arranque' in driver.current_url:
        btn = _wait(driver, By.ID, 'IMAGE2', clickable=True)
        if btn:
            _click(driver, btn)
            time.sleep(SLEEP_SHORT)

    # Fill login form
    user_field = _wait(driver, By.NAME, 'vUSUARIO')
    if not user_field:
        print('[login] ERROR: vUSUARIO field not found')
        return False
    user_field.clear()
    user_field.send_keys(USERNAME)

    pass_field = _wait(driver, By.NAME, 'vCLAVE')
    if not pass_field:
        print('[login] ERROR: vCLAVE field not found')
        return False
    pass_field.clear()
    pass_field.send_keys(PASSWORD)

    submit = _wait(driver, By.NAME, 'BUTTON1', clickable=True)
    if not submit:
        print('[login] ERROR: BUTTON1 not found')
        return False
    _click(driver, submit)
    time.sleep(SLEEP_LONG)

    ok = 'menuprincipal' in driver.current_url
    print(f'[login] {"OK" if ok else "FAILED"} — {driver.current_url}')
    return ok


def ensure_session(driver):
    """Re-login if session has expired."""
    if not is_session_alive(driver):
        print('[ensure_session] Session expired, re-logging in...')
        return login(driver)
    return True


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def go_to_mascotas(driver):
    """
    From menuprincipal, click MASCOTAS and wait for todasmascotas.
    Returns True on success.
    """
    btn = _wait(driver, By.ID, 'MASCOTAS', clickable=True)
    if not btn:
        print('[go_to_mascotas] MASCOTAS button not found')
        return False
    _click(driver, btn)
    time.sleep(SLEEP_MEDIUM)
    ok = 'todasmascotas' in driver.current_url
    print(f'[go_to_mascotas] {"OK" if ok else "FAILED"} — {driver.current_url}')
    return ok


def search_case(driver, case_number):
    """
    In todasmascotas, type case_number in vMASCOTASNRO and read the grid.

    Returns dict with keys:
        especie (str | None)   — e.g. 'CANINO', 'FELINO'
        cedula_link (WebElement) — the <a> in the cedula column

    Returns None if the case does not exist in the system.
    """
    # Ensure we are on todasmascotas
    if 'todasmascotas' not in driver.current_url:
        driver.get(MASCOTAS_URL)
        time.sleep(SLEEP_MEDIUM)

    field = _wait(driver, By.ID, 'vMASCOTASNRO')
    if not field:
        print(f'[search_case] vMASCOTASNRO not found')
        return None

    field.clear()
    field.send_keys(case_number)
    time.sleep(SLEEP_SHORT)

    # Wait for grid to populate
    table = _wait(driver, By.ID, 'Grid1ContainerTbl', timeout=WAIT_TIMEOUT)
    if not table:
        print(f'[search_case] {case_number} — grid not found')
        return None

    # Check if there are result rows (not just header)
    try:
        rows = table.find_elements(By.TAG_NAME, 'tr')
        data_rows = [r for r in rows if r.find_elements(By.TAG_NAME, 'td')]
        if not data_rows:
            print(f'[search_case] {case_number} — no results')
            return None
    except Exception as e:
        print(f'[search_case] {case_number} — error reading grid: {e}')
        return None

    # Read especie from the first data row (look for a cell with a known species)
    especie = None
    cedula_link = None
    first_row = data_rows[0]
    cells = first_row.find_elements(By.TAG_NAME, 'td')

    for cell in cells:
        text = cell.text.strip().upper()
        if text in SPECIES_VALID:
            especie = 'FELINO' if text == 'FELINA' else text
        # Cedula link is the first <a> in the row
        if cedula_link is None:
            links = cell.find_elements(By.TAG_NAME, 'a')
            if links:
                cedula_link = links[0]

    if cedula_link is None:
        print(f'[search_case] {case_number} — cedula link not found')
        return None

    _wait_mask_gone(driver)
    print(f'[search_case] {case_number} — especie={especie}')
    return {'especie': especie, 'cedula_link': cedula_link}


def get_pet_row(driver, case_number):
    """
    In wwmascotas (after clicking mostrar mascotas), find the row index
    whose Nro column matches case_number.

    Returns 1-based row index (int) or None.
    """
    time.sleep(SLEEP_MEDIUM)

    # Find all vBOTONFICHA_XXXX buttons
    try:
        buttons = driver.find_elements(By.XPATH, '//*[starts-with(@id,"vBOTONFICHA_")]')
        if not buttons:
            print(f'[get_pet_row] No ficha buttons found')
            return None
    except Exception as e:
        print(f'[get_pet_row] Error: {e}')
        return None

    # Try to find the Nro column for each row
    # GeneXus grid rows: each row has a Nro cell we can match
    # Row button IDs are vBOTONFICHA_0001, vBOTONFICHA_0002, etc.
    for btn in buttons:
        btn_id = btn.get_attribute('id')  # e.g. vBOTONFICHA_0001
        row_suffix = btn_id.split('_')[-1]  # e.g. 0001

        # Look for the Nro cell in the same row (id pattern: vMASCOTASNRO_XXXX or cell in same tr)
        try:
            # Try to find the Nro span/cell in the same table row
            row_el = btn.find_element(By.XPATH, './ancestor::tr[1]')
            row_text = row_el.text
            # Normalize case number format for comparison (0001/2023)
            norm = case_number.strip()
            if norm in row_text:
                idx = int(row_suffix)
                print(f'[get_pet_row] Found {case_number} at row {idx}')
                return idx
        except NoSuchElementException:
            continue

    # If only one mascota, just return 1
    if len(buttons) == 1:
        print(f'[get_pet_row] Single mascota, using row 1')
        return 1

    print(f'[get_pet_row] Could not match {case_number} in any row')
    return None


def get_ficha_buttons(driver):
    """
    In wwfichas, return list of print button IDs ordered from oldest to newest
    (highest index first = oldest consultation).

    Returns list of str like ['vBOTONIMPRIMIR_0003', 'vBOTONIMPRIMIR_0002', ...]
    """
    time.sleep(SLEEP_MEDIUM)
    try:
        buttons = driver.find_elements(By.XPATH, '//*[starts-with(@id,"vBOTONIMPRIMIR_")]')
        if not buttons:
            print('[get_ficha_buttons] No print buttons found')
            return []

        # Sort by numeric index descending (highest = oldest)
        def index_of(btn):
            m = re.search(r'(\d+)$', btn.get_attribute('id'))
            return int(m.group(1)) if m else 0

        sorted_btns = sorted(buttons, key=index_of, reverse=True)
        ids = [b.get_attribute('id') for b in sorted_btns]
        print(f'[get_ficha_buttons] {len(ids)} buttons, oldest first: {ids}')
        return ids
    except Exception as e:
        print(f'[get_ficha_buttons] Error: {e}')
        return []


def _cleanup_download_dir(download_dir):
    """Remove all aimpresionuno* files (PDFs and .crdownload) from download_dir."""
    import glob as _glob
    for f in _glob.glob(os.path.join(download_dir, 'aimpresionuno*')):
        try:
            os.remove(f)
        except OSError:
            pass


def download_ficha(driver, btn_id, download_dir):
    """
    Click the print button identified by btn_id and wait for the PDF to download.

    Returns the full path of the downloaded PDF, or None on failure.
    """
    btn = _wait(driver, By.ID, btn_id, clickable=True)
    if not btn:
        print(f'[download_ficha] Button {btn_id} not found')
        return None

    # Clean ALL aimpresionuno* files so Chrome uses the base filename
    _cleanup_download_dir(download_dir)

    _click(driver, btn)
    print(f'[download_ficha] Clicked {btn_id}, waiting for download...')

    result = _wait_for_download(download_dir)
    if result:
        print(f'[download_ficha] Downloaded: {result}')
    else:
        print(f'[download_ficha] Timeout waiting for download')
    return result


def _wait_for_download(download_dir, timeout=None):
    """
    Wait until any aimpresionuno*.pdf (without .crdownload) appears in download_dir.
    Returns the path or None on timeout or shutdown.
    """
    import glob as _glob
    import scraper as _scraper_mod
    t = timeout or DOWNLOAD_TIMEOUT
    start = time.time()
    last_size = {}
    stable_count = {}

    while time.time() - start < t:
        if getattr(_scraper_mod, 'is_shutting_down', False):
            return None

        # Check for completed PDFs (any aimpresionuno*.pdf not ending in .crdownload)
        pdfs = [f for f in _glob.glob(os.path.join(download_dir, 'aimpresionuno*.pdf'))
                if not f.endswith('.crdownload')]
        if pdfs:
            return pdfs[0]

        # Monitor .crdownload files for stability
        crs = _glob.glob(os.path.join(download_dir, 'aimpresionuno*.crdownload'))
        for cr in crs:
            try:
                size = os.path.getsize(cr)
            except OSError:
                continue
            if last_size.get(cr) == size:
                stable_count[cr] = stable_count.get(cr, 0) + 1
                if stable_count[cr] >= 3:
                    pdf_path = cr.replace('.crdownload', '')
                    try:
                        os.rename(cr, pdf_path)
                        return pdf_path
                    except OSError:
                        pass
            else:
                last_size[cr] = size
                stable_count[cr] = 0

        time.sleep(1)

    return None
