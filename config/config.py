# Scraper Configuration
import os
from dotenv import load_dotenv

load_dotenv()

# URLs
BASE_URL = os.environ.get('BASE_URL', 'http://164.73.21.67:8080/hospital7.0d')
ARRANQUE_URL = os.environ.get('ARRANQUE_URL', f'{BASE_URL}/com.hospital.arranque')
LOGIN_URL = f'{BASE_URL}/com.hospital.login'
MASCOTAS_URL = f'{BASE_URL}/com.hospital.todasmascotas'

# Credentials
USERNAME = os.environ['USERNAME']
PASSWORD = os.environ['PASSWORD']

# Case range
START_CASE = 1
END_CASE = 3279
YEAR = 2023

# Paths
DOWNLOAD_DIR = 'downloads'
OUTPUT_DIR = 'output'
OUTPUT_EXCEL = f'{OUTPUT_DIR}/resultados_{YEAR}.xlsx'
MISSING_CASES_FILE = f'{OUTPUT_DIR}/missing_cases.txt'
ERRORS_FILE = f'{OUTPUT_DIR}/errors.txt'

# Timing
WAIT_TIMEOUT = 10       # seconds to wait for elements
DOWNLOAD_TIMEOUT = 120  # seconds to wait for PDF download
SLEEP_SHORT = 2
SLEEP_MEDIUM = 3
SLEEP_LONG = 5

# Request settings
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

# Save Excel every N cases
SAVE_EVERY = 50
