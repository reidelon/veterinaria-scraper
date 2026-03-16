"""
csv_writer.py — CSV output module for hospital scraper.
"""

import csv
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.config import OUTPUT_DIR, YEAR

OUTPUT_CSV = os.path.join(OUTPUT_DIR, f'resultados_{YEAR}.csv')

COLUMNS = [
    'Nro Ficha',
    'Especie',
    'Sexo',
    'Edad (años)',
    'Raza',
    'Peso (kg)',
    'Tamaño',
    'Departamento',
    'Paraje',
    'Especialidad',
    'Motivo Consulta',
    'Examen Obj. Particular',
]


def init_csv():
    """
    Create output dir and CSV with header if it doesn't exist yet.
    Returns the path to the CSV file.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
        print(f'[csv_writer] Created {OUTPUT_CSV}')
    else:
        print(f'[csv_writer] Appending to existing {OUTPUT_CSV}')
    return OUTPUT_CSV


def write_row(fields, case_number):
    """
    Append one row to the CSV.

    fields: dict as returned by pdf_extractor.extract_fields()
    case_number: str like "0001/2023"
    """
    row = {
        'Nro Ficha':            case_number,
        'Especie':              fields.get('especie') or '',
        'Sexo':                 fields.get('sexo') or '',
        'Edad (años)':          fields.get('edad') if fields.get('edad') is not None else '',
        'Raza':                 fields.get('raza') or '',
        'Peso (kg)':            fields.get('peso_kg') if fields.get('peso_kg') is not None else '',
        'Tamaño':               fields.get('tamano') or '',
        'Departamento':         fields.get('departamento') or '',
        'Paraje':               fields.get('paraje') or '',
        'Especialidad':         fields.get('especialidad') or '',
        'Motivo Consulta':      fields.get('motivo_consulta') or '',
        'Examen Obj. Particular': fields.get('examen_objetivo') or '',
    }
    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writerow(row)


def get_processed_cases():
    """
    Read the CSV and return a set of already-processed case numbers.
    Used at startup to resume without duplicating rows.
    """
    if not os.path.exists(OUTPUT_CSV):
        return set()
    processed = set()
    with open(OUTPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            nro = row.get('Nro Ficha', '').strip()
            if nro:
                processed.add(nro)
    print(f'[csv_writer] {len(processed)} cases already processed')
    return processed
