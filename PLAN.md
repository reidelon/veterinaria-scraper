# Plan de Ejecución — Hospital Scraper

## Índice

1. [Contexto y estado actual](#1-contexto-y-estado-actual)
2. [Hallazgos técnicos de la simulación](#2-hallazgos-técnicos-de-la-simulación)
3. [Estructura del flujo navegación](#3-estructura-del-flujo-de-navegación)
4. [Campos a extraer y reglas](#4-campos-a-extraer-y-reglas)
5. [Edge cases confirmados](#5-edge-cases-confirmados)
6. [Plan de subtareas](#6-plan-de-subtareas)
   - [T1 — Configuración y setup](#t1--configuración-y-setup)
   - [T2 — Módulo de navegación Selenium](#t2--módulo-de-navegación-selenium)
   - [T3 — Módulo de extracción PDF](#t3--módulo-de-extracción-pdf)
   - [T4 — Módulo de output Excel](#t4--módulo-de-output-excel)
   - [T5 — Loop principal con resumibilidad](#t5--loop-principal-con-resumibilidad)
   - [T6 — Prueba end-to-end con 10 casos](#t6--prueba-end-to-end-con-10-casos)
7. [Estructura de archivos propuesta](#7-estructura-de-archivos-propuesta)
8. [Preguntas aún pendientes](#8-preguntas-aún-pendientes)

---

## 1. Contexto y estado actual

**Objetivo:** Extraer datos clínicos de 3279 fichas veterinarias (0001/2023 a 3279/2023) del sistema web del Hospital de la Facultad de Veterinaria (FVET - UdelaR) y guardarlos en un Excel. Es para una tesis de grado (usuario: johana.long).

**Estado del código:** `src/scraper.py` fue escrito para la versión anterior del sistema (`hospital5.7f`) y está incompleto — tiene dos `breakpoint()` activos y lógica sin terminar. Hay que reescribirlo casi completamente para `hospital7.0d`.

**URL nueva:** `http://164.73.21.67:8080/hospital7.0d/com.hospital.arranque`

---

## 2. Hallazgos técnicos de la simulación

Se simuló el flujo completo contra el servidor real. Resultados clave:

- La app es **GeneXus full-AJAX**. `curl` no sirve, Selenium es obligatorio.
- El flujo de navegación fue validado exitosamente hasta descarga de PDF.
- El PDF descarga siempre con el nombre fijo `aimpresionuno_impl.pdf` (igual que en `hospital5.7f`).
- **La Especie está visible en el grid de búsqueda** (`com.hospital.todasmascotas`) antes de entrar a la ficha. Esto permite filtrar canino/felino sin descargar ningún PDF, ahorrando clics en todos los casos que no aplican.
- El campo `Edad:` en el PDF ya está en **años enteros** (ej: 5 meses → `Edad: 0`). No hay que parsear texto narrativo para la edad.
- El PDF tiene extracción de texto desordenada por el layout — los campos de dirección/paraje salen en orden inverso al visual.

**IDs de los elementos Selenium confirmados:**

| Elemento | ID/selector |
|---|---|
| Botón Hospital (pantalla inicial) | `IMAGE2` |
| Campo usuario login | `vUSUARIO` |
| Campo contraseña login | `vCLAVE` |
| Botón ingresar | `BUTTON1` |
| Botón Mascotas (menú) | `MASCOTAS` |
| Campo número de ficha | `vMASCOTASNRO` |
| Link cédula en grid resultados | `#Grid1ContainerTbl a` (primer `<a>`) |
| Ícono caballo (mostrar mascotas) | `vBOTONMASCOTA_0001` |
| Ícono calendario (ir a fichas) | `vBOTONFICHA_0001` |
| Botones imprimir en lista fichas | `vBOTONIMPRIMIR_XXXX` (el de índice más alto = consulta más antigua) |

---

## 3. Estructura del flujo de navegación

```
[arranque]
    → clic IMAGE2
[login: com.hospital.login?Ubicacion=verde]
    → ingresar vUSUARIO + vCLAVE → clic BUTTON1
[menuprincipal: com.hospital.menuprincipal]
    → clic MASCOTAS
[todasmascotas: com.hospital.todasmascotas]
    → escribir NNNN/2023 en #vMASCOTASNRO
    → leer Especie del grid
    → si Especie != CANINO/FELINO → siguiente número (NO entrar)
    → clic link cédula en #Grid1ContainerTbl
[wwclientes: com.hospital.wwclientes]
    → clic vBOTONMASCOTA_0001
[wwmascotas: com.hospital.wwmascotas]
    → identificar la fila cuyo Nro == NNNN/2023
    → clic vBOTONFICHA_XXXX de esa fila
[wwfichas: com.hospital.wwfichas]
    → contar todos los botones vBOTONIMPRIMIR_XXXX
    → clic en el de índice MÁS ALTO (= consulta más antigua)
    → esperar descarga de aimpresionuno_impl.pdf
    → renombrar a NNNN_2023.pdf en /downloads
    → extraer campos del PDF
    → si motivo/examen vacíos → clic en el segundo más alto, etc.
    → volver a todasmascotas para el siguiente número
```

**Nota sobre múltiples mascotas por propietario:**
En `wwmascotas` puede haber más de una fila. Hay que hacer match por el campo `Nro` de la grilla con el número de ficha que se está procesando. En el HTML, los botones siguen el patrón `vBOTONFICHA_0001`, `vBOTONFICHA_0002`, etc. — hay que recorrerlos y verificar cuál corresponde al número correcto antes de hacer clic.

---

## 4. Campos a extraer y reglas

Todos se extraen del PDF descargado salvo donde se indica.

| Campo Excel | Fuente | Regla / Notas |
|---|---|---|
| Número de ficha | grid búsqueda | Ej: `0001/2023` |
| Especie | grid búsqueda | Solo `CANINO` o `FELINO` |
| Sexo | PDF campo `Sexo:` | M → Macho / F → Hembra |
| Edad | PDF campo `Edad:` | En años enteros. 5 meses = 0 años |
| Raza | PDF campo `Raza` | Texto literal |
| Peso | PDF campo `Peso (grs.)` | **Solo si** Especie=CANINO y Raza contiene "Cruza". Convertir grs → kg. Felinos: nunca registrar peso. |
| Clasificación tamaño | calculado | Solo perro cruza: ≤10kg=chico, ≤20kg=mediano, >20kg=grande |
| Departamento | PDF sección cliente | Campo `Departamento` |
| Paraje o barrio | PDF sección cliente | Campo `Paraje`. Si vacío, parsear desde `Dirección` |
| Especialidad | PDF campo `Especialidad:` | Texto literal |
| Motivo de consulta | PDF sección `Motivo Consulta:` | Si vacío en consulta más antigua → buscar en siguientes consultas. Si ninguna tiene → dejar en blanco |
| Examen obj. particular | PDF sección `Examen Objetivo Particular` | Igual que motivo consulta para el fallback |

**Regla de fallback para motivo/examen:**
```
Para cada ficha canino/felino:
  1. Descargar PDF de consulta más antigua (botón de índice más alto)
  2. Extraer motivo y examen
  3. Si alguno está vacío:
     a. Volver a wwfichas
     b. Bajar al siguiente botón (segundo más alto) y descargar
     c. Completar solo los campos que siguen vacíos
     d. Repetir hasta llenar ambos o agotar consultas
  4. Si se agotan las consultas con campos vacíos → dejar en blanco
```

---

## 5. Edge cases confirmados

| # | Situación | Acción |
|---|---|---|
| 1 | Número de ficha no existe en el sistema | Loguear en `missing_cases.txt`, continuar |
| 2 | Especie ≠ Canino/Felino | Saltar (la especie se ve en el grid, sin descargar PDF) |
| 3 | Propietario tiene 1 sola mascota | Usarla directamente |
| 4 | Propietario tiene N mascotas | Hacer match por campo `Nro` == número de ficha actual |
| 5 | Mascota tiene 1 sola consulta con motivo/examen vacíos | Dejar en blanco |
| 6 | Peso = 0 en un perro cruza | Registrar 0, clasificar como "chico" (≤10kg) |
| 7 | Edad = 0 años | Registrar 0 |
| 8 | Raza cruza en Felino | NO registrar peso |
| 9 | PDF no descarga / timeout | Loguear en `errors.txt`, continuar |
| 10 | Sesión expira (proceso de horas) | Detectar redirección a login y re-autenticar automáticamente |
| 11 | Paraje vacío en PDF | Parsear campo `Dirección` como fallback |

---

## 6. Plan de subtareas

### T1 — Configuración y setup

**Archivos a modificar:** `src/scraper.py`, `config/config.py`

- [ ] Actualizar URL base a `hospital7.0d`
- [ ] Mover credenciales y URLs a `config/config.py` (sacarlas del hardcode en scraper.py)
- [ ] Agregar a config: rango de casos (`START=1`, `END=3279`), año (`2023`), paths de output
- [ ] Eliminar los dos `breakpoint()` activos (líneas 543 y 580 del scraper actual)
- [ ] Verificar que `requirements.txt` tiene todo lo necesario (`openpyxl` para Excel)

---

### T2 — Módulo de navegación Selenium

**Archivo:** `src/navigator.py` (nuevo)

Encapsular toda la lógica de Selenium en funciones reutilizables:

- [ ] `login(driver)` — arranque → Hospital → credenciales → menuprincipal
- [ ] `go_to_mascotas(driver)` — desde menuprincipal → todasmascotas
- [ ] `search_case(driver, case_number) -> dict|None` — escribe el número, lee el grid. Retorna `{especie, cedula_element}` o `None` si no existe
- [ ] `get_pet_row(driver, case_number) -> int|None` — en wwmascotas, devuelve el índice de fila que corresponde al número de ficha
- [ ] `get_ficha_buttons(driver) -> list[str]` — en wwfichas, retorna lista de IDs de botones imprimir ordenados de más antiguo a más reciente (índice más alto = más antiguo)
- [ ] `download_ficha(driver, btn_id, download_dir) -> str|None` — clic en botón imprimir, espera descarga, retorna path del PDF
- [ ] `is_session_alive(driver) -> bool` — verifica si la sesión sigue activa (detecta redirección a login)
- [ ] `ensure_session(driver)` — llama a `login()` si la sesión expiró

---

### T3 — Módulo de extracción PDF

**Archivo:** `src/pdf_extractor.py` (nuevo)

- [ ] `extract_fields(pdf_path) -> dict` — extrae todos los campos del PDF:
  - Especie, Sexo, Edad (campo numérico), Raza, Peso (grs)
  - Departamento, Paraje (con fallback a Dirección)
  - Especialidad
  - Motivo de consulta
  - Examen objetivo particular
- [ ] Manejar el orden inverso del texto PDF para campos de dirección (regex robustos)
- [ ] Para Motivo de consulta: buscar entre `Motivo Consulta:` y `ANAMNESIS` o siguiente sección
- [ ] Para Examen objetivo particular: buscar sección `Examen Objetivo Particular` hasta `DIAGNOSTICO`
- [ ] Retornar `None` en campos no encontrados (no lanzar excepción)
- [ ] `is_data_complete(fields) -> bool` — True si motivo y examen no son None/vacío

---

### T4 — Módulo de output Excel

**Archivo:** `src/excel_writer.py` (nuevo)

- [ ] Crear/abrir `output/resultados_2023.xlsx` al inicio
- [ ] Columnas en orden: Nro Ficha, Especie, Sexo, Edad (años), Raza, Peso (kg), Tamaño, Departamento, Paraje, Especialidad, Motivo Consulta, Examen Obj. Particular
- [ ] `write_row(wb, data_dict)` — agrega una fila
- [ ] `save(wb)` — guarda el archivo (llamar cada N casos para no perder progreso)
- [ ] `get_processed_cases(wb) -> set` — leer los números de ficha ya escritos (para resumir)

---

### T5 — Loop principal con resumibilidad

**Archivo:** `src/scraper.py` (reescribir)

- [ ] Al inicio, leer Excel existente para saber qué casos ya están procesados → saltarlos
- [ ] Al inicio, leer `missing_cases.txt` → saltarlos también
- [ ] Loop `for i in range(START, END+1)`:
  - Formatear: `case = f"{i:04d}/2023"`
  - Si ya procesado → skip
  - `search_case()` → si None → loguear en missing_cases.txt → continue
  - Si especie != CANINO/FELINO → continue (sin loguear, es esperado)
  - Navegar hasta wwfichas
  - Loop de descarga con fallback para motivo/examen vacíos
  - Extraer campos del PDF
  - Calcular tamaño si aplica
  - Escribir fila en Excel
  - Guardar Excel cada 50 casos
  - Volver a todasmascotas para el siguiente
- [ ] Manejo de Ctrl+C graceful (guardar antes de salir)
- [ ] Re-login automático si sesión expiró

---

### T6 — Prueba end-to-end con 10 casos

Antes de correr los 3279 casos, validar con una muestra:

- [ ] Correr casos 0001/2023 a 0010/2023
- [ ] Verificar Excel generado manualmente contra los PDFs
- [ ] Verificar que `missing_cases.txt` y `errors.txt` se generan correctamente
- [ ] Verificar resumibilidad: interrumpir a mitad y volver a correr — no debe duplicar filas
- [ ] Ajustar tiempos de espera (`time.sleep`) si hay timeouts
- [ ] Confirmar que la sesión se recupera correctamente

---

## 7. Estructura de archivos propuesta

```
hospital_scraper/
├── config/
│   └── config.py          # URLs, credenciales, rango casos, paths
├── src/
│   ├── scraper.py          # Loop principal (reescribir)
│   ├── navigator.py        # Módulo Selenium (nuevo)
│   ├── pdf_extractor.py    # Módulo PyPDF2 (nuevo)
│   └── excel_writer.py     # Módulo openpyxl (nuevo)
├── downloads/              # PDFs temporales (se pueden borrar después)
├── output/
│   ├── resultados_2023.xlsx
│   ├── missing_cases.txt   # Fichas que no existen en el sistema
│   └── errors.txt          # Errores de descarga/extracción
├── requirements.txt
└── PLAN.md
```

---

## 8. Preguntas aún pendientes

Estas preguntas quedaron sin respuesta y pueden requerir decisión antes de implementar T3/T4:

| # | Pregunta | Impacto |
|---|---|---|
| A | ¿Cómo identificar "perro cruza"? ¿El campo Raza dice literalmente "Cruza" o puede ser "Mestizo", "SRD", etc.? | Lógica del campo Peso y Tamaño |
| B | ¿Qué hacer si Paraje Y Dirección están vacíos? | Dejar en blanco o marcar como "sin dato" |
| C | ¿El Excel tiene un formato/plantilla predefinido o se crea desde cero? | Diseño de columnas en T4 |
| D | ¿Cuántos casos aproximadamente se espera que no sean Canino/Felino? (para estimar tiempo total) | Planificación |
