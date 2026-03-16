# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the scraper
python src/scraper.py
```

There are no tests or linting configurations in this project.

## Architecture

This is a single-file Selenium scraper (`src/scraper.py`) that automates a Chrome browser to log into a hospital management web app, search for patient cases by case number, navigate through the UI, download PDF records, and extract structured data from those PDFs.

**Flow:**
1. Reads already-downloaded PDFs from `downloads/` to skip re-processing
2. Logs into the hospital web app via form submission
3. For each case number in the `case_numbers` list, searches the patient grid, navigates to the patient detail, then to the pet (mascota) record, and triggers a PDF download
4. Waits for the `.crdownload` file to complete, then renames it to `NNNN_YYYY.pdf`
5. Parses the renamed PDF with PyPDF2 to extract `Raza` and `Especialidad` fields

**Key details:**
- Case numbers use format `NNNN/YYYY` (e.g., `"0009/2023"`); slashes are replaced with underscores for filenames
- The `case_numbers` list (line 381) is a module-level variable that executes at import time — it is currently hardcoded to two cases
- The target URLs and credentials are hardcoded at the top of `scraper.py` (not in `config/config.py`, which is largely unused)
- `config/config.py` defines constants like `REQUEST_TIMEOUT`, `BATCH_SIZE`, etc., but these are not currently imported or used by `scraper.py`
- There are two `breakpoint()` calls left in `main()` (lines 543 and 580) from debugging — these will pause execution
- Chrome is configured to auto-download PDFs to `./downloads/` and bypass SSL errors for the HTTP target server
- Graceful shutdown is handled via `SIGINT` — pressing Ctrl+C sets `is_shutting_down = True` and allows in-progress downloads to finish
