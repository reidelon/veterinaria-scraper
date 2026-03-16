# Hospital Scraper

A Python-based web scraper for collecting veterinary hospital information.

## Setup

1. Make sure you have Python 3.8+ installed
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   .\venv\Scripts\activate  # On Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure

- `src/` - Source code directory
  - `scraper.py` - Main scraper implementation
  - `utils.py` - Utility functions
- `data/` - Directory for storing scraped data
- `config/` - Configuration files
- `requirements.txt` - Project dependencies
- `README.md` - This file

## Usage

1. Configure your settings in `config/config.py`
2. Run the scraper:
   ```bash
   python src/scraper.py
   ```

## Data Output

Scraped data will be saved in the `data/` directory in CSV format. 
