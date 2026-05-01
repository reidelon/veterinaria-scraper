# Instalación en Windows — Paso a Paso

## Requisitos previos (instalar una sola vez)

### 1. Python
- Ir a **python.org/downloads**
- Descargar el instalador (botón amarillo grande)
- Al instalar: marcar **"Add Python to PATH"** antes de hacer clic en Install
- Verificar en CMD: `python --version`

### 2. Git
- Ir a **git-scm.com/download/win**
- Instalar con opciones por defecto
- Verificar en CMD: `git --version`

### 3. Google Chrome
- Instalar normalmente si no lo tiene
- El scraper usa Chrome para automatizar el navegador

---

## Instalación del proyecto

### 4. Clonar el repositorio
Abrir CMD o PowerShell y ejecutar:
```cmd
git clone https://github.com/reidelon/veterinaria-scraper.git
cd veterinaria-scraper
```

### 5. Crear entorno virtual e instalar dependencias
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 6. Crear el archivo de credenciales
El scraper necesita usuario y contraseña para entrar al sistema del hospital. Estos datos **no están en GitHub** por seguridad — hay que crearlos a mano en un archivo llamado `.env`.

Desde el CMD, estando dentro de la carpeta `veterinaria-scraper`, ejecutar estos tres comandos uno por uno (reemplazar `USUARIO` y `CONTRASEÑA` con los datos reales):

```cmd
echo BASE_URL=http://164.73.21.67:8080/hospital7.0d > .env
echo HOSPITAL_USERNAME=USUARIO >> .env
echo HOSPITAL_PASSWORD=CONTRASEÑA >> .env
```

Para verificar que quedó bien creado:
```cmd
type .env
```

Debería mostrar:
```
BASE_URL=http://164.73.21.67:8080/hospital7.0d
HOSPITAL_USERNAME=USUARIO
HOSPITAL_PASSWORD=CONTRASEÑA
```

---

## Continuar desde donde quedó (no empezar de cero)

Los datos ya procesados **no están en GitHub**. Para no reprocesar todo hay que copiar desde la PC Linux:

### 7. Copiar los archivos de progreso
Hay un archivo `hospital_scraper.zip` con todos los datos ya procesados. Contiene:
- `output/resultados_2023.csv` — todas las fichas extraídas hasta ahora
- `output/errores.csv` — fichas con error
- `output/missing_cases.txt` — fichas no encontradas
- `downloads/0299_2023.pdf` — último PDF descargado

Pasos:
1. Copiar `hospital_scraper.zip` a la PC Windows (por USB o Google Drive)
2. Extraer el zip **dentro de la carpeta `veterinaria-scraper\`**
3. Los archivos van a quedar en el lugar correcto automáticamente

---

## Correr el scraper

### 8. Activar el entorno e iniciar
```cmd
cd veterinaria-scraper
venv\Scripts\activate
python src\scraper.py
```

Al arrancar pregunta:
```
¿Mostrar ventana del navegador? [s/N]
```
- Escribir `s` + Enter para ver el navegador (útil para depurar)
- Enter o silencio (5 segundos) para modo oculto (headless)

---

## Posibles problemas

| Problema | Solución |
|---|---|
| `python` no reconocido | Reinstalar Python marcando "Add to PATH" |
| `venv\Scripts\activate` bloqueado | Ejecutar en PowerShell: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Chrome no abre | Verificar que Google Chrome esté instalado |
| Error de credenciales | Verificar que el archivo `.env` existe y tiene los datos correctos |
