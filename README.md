# Bots Sofia Plus

Base modular para bots de Sena Sofia Plus.

## Modulos creados

- `sofia_bots/settings.py`: configuracion, credenciales por variables de entorno y carpetas.
- `sofia_bots/browser.py`: sesion Playwright con reinicio automatico y reintentos.
- `sofia_bots/sofia.py`: login, seleccion de rol, apertura de rutas de menu y validacion basica de sesion.
- `sofia_bots/downloads.py`: descargas con `expect_download`, nombres unicos y opcion de sobrescritura.
- `sofia_bots/control.py`: bitacora Excel para evitar duplicados y registrar errores.
- `sofia_bots/credential_store.py`: guarda y reutiliza credenciales en `.env`.
- `sofia_bots/inasistencias_cleaner.py`: limpieza FSM del consolidado y salida lista para Power BI.
- `sofia_bots/multi.py`: utilidad simple para repartir tareas entre varios bots/hilos.
- `bots/descargar_inasistencias.py`: primer bot modular para descargar el consolidado de inasistencias.

## Credenciales

Ejecuta exactamente esto (en orden):

cd "C:\Users\capatino\Documents\Software con códex"


El nuevo bot no deja usuario ni clave escritos dentro del codigo. La forma
recomendada es dejar que el propio bot las guarde en `.env` la primera vez.

### Primera ejecucion (recomendada)

1. Ejecuta el bot interactivo:

   ```powershell
   ejecutar_inasistencias.bat
   ```

2. Ingresa tu documento y contrasena en el cuadro que aparece.
3. El bot escribe `SOFIA_USUARIO` y `SOFIA_PASSWORD` en `.env` y no vuelve a
   pedirlas en las siguientes ejecuciones.

Vuelve a ejecutarlo con el cuadro solo si SENA Sofia Plus te obliga a cambiar la
contrasena. El bot detecta el rechazo del ingreso y te la pide de nuevo; la clave
nueva reemplaza la anterior en `.env`.

Para forzar el cambio de credenciales manualmente:

```powershell
python -m bots.descargar_inasistencias --pedir-credenciales --forzar-credenciales
```

El archivo `.env` esta en `.gitignore`; la contrasena nunca se imprime en
consola ni se escribe en los logs.

### Opcion manual: archivo .env

Si prefieres escribirlas tu, copia `.env.example` como `.env` en la raiz del
proyecto:

```text
C:\Users\capatino\Documents\Software con códex\.env
```

Contenido minimo:

```text
SOFIA_USUARIO=tu_documento
SOFIA_PASSWORD=tu_clave
```

La carpeta de salida es, por defecto:

```text
<Escritorio>\Inasistencias
```

El bot la crea una sola vez si no existe. Para usar otra ruta:

```text
INASISTENCIAS_SALIDA=C:\Users\capatino\Desktop\Inasistencias
```

El modulo `sofia_bots/settings.py` lee este archivo automaticamente cuando ejecutas el bot desde la carpeta del proyecto.

### Opcion alternativa: variables de Windows

En PowerShell puedes definirlas solo para la terminal actual:

```powershell
$env:SOFIA_USUARIO="tu_documento"
$env:SOFIA_PASSWORD="tu_clave"
```

O dejarlas persistentes para tu usuario de Windows:

```powershell
setx SOFIA_USUARIO "tu_documento"
setx SOFIA_PASSWORD "tu_clave"
```

Despues de usar `setx`, cierra y vuelve a abrir VS Code o la terminal para que las variables aparezcan.

## Ejecutar descarga de inasistencias

### Desde el icono o el boton de Power BI

Para uso manual desde un icono de escritorio, desde el boton de Power BI o
desde el lanzador:

```powershell
ejecutar_inasistencias.bat
```

Ese lanzador abre el cuadro de credenciales **solo si no hay datos guardados en
`.env`** o si Sofia Plus rechaza el ingreso. En ejecuciones posteriores reutiliza
las credenciales y no muestra ningun cuadro.

Comando equivalente:

```powershell
python -m bots.sofiabot_inasistencias_app
```

Para generar un ejecutable de escritorio:

```powershell
crear_ejecutable_sofiabot.bat
```

El ejecutable queda en `dist\SOFIABOT_Inasistencias.exe`.

### Crear ejecutable e icono de escritorio

Procedimiento completo:

1. Abre PowerShell en la raiz del proyecto:

```powershell
cd "C:\Users\capatino\Documents\Software con códex"
```

2. Activa el entorno virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Instala o actualiza dependencias:

```powershell
python -m pip install -r requirements.txt
```

4. Genera el ejecutable completo:

```powershell
.\crear_ejecutable_sofiabot.bat
```

Este proceso instala/valida dependencias, instala Chromium de Playwright y empaca el bot con el navegador incluido.

5. El ejecutable completo queda en:

```text
C:\Users\capatino\Documents\Software con códex\dist\SOFIABOT_Inasistencias_Completo.exe
```

6. Para crear manualmente el acceso directo en el escritorio:

```powershell
$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'SOFIABOT Inasistencias.lnk'
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = 'C:\Users\capatino\Documents\Software con códex\dist\SOFIABOT_Inasistencias_Completo.exe'
$Shortcut.WorkingDirectory = 'C:\Users\capatino\Documents\Software con códex'
$Shortcut.IconLocation = 'C:\Users\capatino\Documents\Software con códex\assets\SOFIABOT.ico'
$Shortcut.Description = 'Descarga el reporte de inasistencias desde Sofia Plus'
$Shortcut.Save()
```

Nota: el ejecutable reutiliza las credenciales guardadas en `.env` y solo abre el cuadro la primera vez o cuando Sofia Plus rechaza el ingreso. En otros equipos debe existir Microsoft Excel y Playwright/Chromium debe poder ejecutarse correctamente.

La version completa incluye Chromium dentro del `.exe`, por eso pesa mas y puede tardar unos segundos en abrir la primera vez.

### El ejecutable no muestra ventana

El bot **no es headless por defecto**: abre una ventana de Chromium y navega a
Sofia Plus. Si ves el proceso en el Administrador de tareas pero no aparece
ninguna ventana:

1. Revisa el log:

   ```text
   logs\sofiabot_app.log
   ```

   Si ejecutas el `.exe` desde `dist`, el bot usa el `.env` y la carpeta `logs`
   de la raiz del proyecto para no duplicar configuracion. Si copias el `.exe` a
   otra carpeta, usa la carpeta del ejecutable.

2. Cierra todas las instancias anteriores del bot y vuelve a abrirlo. Un
   ejecutable que ya esta corriendo puede quedar en el ciclo de reintentos.
3. La primera apertura puede tardar por la extraccion del `.exe` (372 MB) y el
   analisis de antivirus. Espera al menos 1-2 minutos.
4. Si el log dice que Chromium no inicio, reinstala el navegador:

   ```powershell
   python -m playwright install chromium
   ```

5. Para forzar un fallo rapido en diagnostico:

   ```powershell
   dist\SOFIABOT_Inasistencias_Completo.exe --reintentos-servidor 1 --espera-servidor 5
   ```

El log tambien registra la ruta del ejecutable, los argumentos y la excepcion
completa si algo falla.

### Con credenciales de .env

Para ejecucion automatica sin intervencion del usuario:

```powershell
python -m bots.descargar_inasistencias
```

Opciones utiles:

```powershell
python -m bots.descargar_inasistencias --fecha-inicio 15/01/2026 --fecha-fin 16/06/2026 --salida "$HOME\Desktop\Reportes inasistencias" --intentos 3
```

Si Sofia Plus no esta disponible al iniciar, el bot reintenta por defecto 60 veces, esperando 60 segundos entre intentos. Para cambiarlo:

```powershell
python -m bots.descargar_inasistencias --reintentos-servidor 120 --espera-servidor 60
```

Para reintentar sin limite:

```powershell
python -m bots.descargar_inasistencias --reintentos-servidor 0
```

Este bot crea una sola vez la carpeta y actualiza siempre el archivo:

```text
C:\Users\capatino\Desktop\Inasistencias\Inasistencias.xls
```

Si el Escritorio esta redirigido a OneDrive, el bot detecta la ruta real desde
el registro de Windows. Tambien puedes fijar otra carpeta con `--salida` o con
`INASISTENCIAS_SALIDA` en `.env`.

Si el archivo ya existe, lo reemplaza de forma atomica. Esto permite programarlo
diariamente desde Power Automate o desde el Programador de tareas de Windows.

Despues de descargar, el bot abre el archivo con Microsoft Excel y renombra la primera hoja a `Inasistencias`. Esto es necesario para que los filtros o conexiones que esperan ese nombre de hoja funcionen correctamente.

## Limpieza automatica del reporte

Inmediatamente despues de la descarga, el bot ejecuta el limpiador FSM del proyecto
`Proyecto Limpiador Inasistencias` sobre el mismo archivo. El resultado reemplaza
`Inasistencias.xls` de forma atomica y queda con el esquema que consume Power BI:

```text
Instructor, Ficha, Programa, Apellidos, Nombres,
Identificacion Aprendiz, Fecha Inicio, Fecha Fin, Cant.horas, Justificacion
```

Notas operativas:

- Si el archivo ya tiene ese esquema, el limpiador no lo vuelve a procesar.
- Si la limpieza falla, el archivo original no se reemplaza y el bot registra el
  error en `control_inasistencias.xlsx`; no reporta exito.
- El reporte de Sofia Plus llega como XLSX aunque el archivo se llame `.xls`; el
  limpiador detecta el formato por contenido.
- Para descargar sin limpiar (solo diagnostico), agrega `--omitir-limpieza`.
- Para ejecutar el limpiador de forma independiente:

```powershell
python -m sofia_bots.inasistencias_cleaner "C:\Ruta\Inasistencias.xls"
```

## Integracion con Power BI y Power Automate

El proyecto incluye dos plantillas de flujo y la consulta M del reporte:

```text
power_automate\flujo_1_boton_powerbi.json
power_automate\flujo_2_programado_1300.json
power_automate\LEEME.md
power_bi\consulta_inasistencias.pq
```

Resumen del flujo:

1. El usuario pulsa el boton del reporte en Power BI.
2. Power Automate ejecuta el flujo de escritorio que corre
   `ejecutar_inasistencias.bat`.
3. La primera vez el bot pide credenciales y las guarda en `.env`.
4. El bot descarga, limpia y reemplaza
   `<Escritorio>\Inasistencias\Inasistencias.xls`.
5. Power BI lee ese archivo y muestra los datos actualizados.
6. Todos los dias a la 1:00 p.m. (hora Colombia) el segundo flujo ejecuta
   `ejecutar_inasistencias_programada.bat` sin intervencion del usuario.

Texto sugerido junto al boton del reporte:

> **Actualizar inasistencias**
> Presiona este boton solo la primera vez. Despues la actualizacion es
> automatica todos los dias a la 1:00 p.m. Vuelve a presionarlo unicamente si
> Sofia Plus te pide cambiar la contrasena.

### Ajustar el .pbix

La consulta actual del reporte debe apuntar a la nueva ruta y **no** debe hacer
`Table.Skip(1)`, porque el archivo limpio ya trae una sola fila de encabezados.
La consulta lista para pegar esta en `power_bi\consulta_inasistencias.pq`.

Pasos:

1. Abre `Reporte personalizado inasistencias Sofía v2.pbix`.
2. **Inicio > Transformar datos > Nueva origen > Consulta en blanco**.
3. **Editor avanzado** y pega el contenido de `consulta_inasistencias.pq`.
4. Ajusta la ruta si tu Escritorio esta en otra ubicacion.
5. **Cerrar y aplicar** y actualiza el reporte.
6. Guarda el `.pbix` y publicalo.

Si el reporte ya tenia una consulta al archivo anterior, reemplaza su codigo M
por este y actualiza las referencias visuales si cambian los nombres de columnas.

### Archivos de Power Automate

Las plantillas no son paquetes `.zip` importables: cada organizacion tiene sus
propias conexiones, maquina y flujo de escritorio. En
`power_automate\LEEME.md` estan los pasos exactos para crear los dos flujos y el
flujo de escritorio que ejecuta los `.bat`.

## Optimizacion de la navegacion (ajustes manuales)

Estos ajustes reducen el tiempo de navegacion, sobre todo la pausa que aparece
despues de ingresar las credenciales. Son cambios manuales: no se aplican solos.

### Causa principal de la demora

En `sofia_bots/sofia.py`, dentro de `select_role`, se espera `networkidle`:

```python
page.wait_for_load_state("networkidle", timeout=10_000)
```

Sofia Plus suele mantener trafico de red abierto, por lo que esa espera casi
siempre agota los 10 segundos y luego continua. El `TimeoutError` se ignora, asi
que la pausa no se nota en el log.

### 1. No esperar todos los recursos al abrir Sofia Plus

En `sofia_bots/sofia.py`, funcion `find_login_frame`:

```python
page.goto(SOFIA_URL, timeout=timeout_ms, wait_until="domcontentloaded")
```

### 2. Esperar el menu real en lugar de `networkidle`

En `sofia_bots/sofia.py`, funcion `select_role`, reemplaza el bloque de
`wait_for_load_state` por:

```python
    try:
        role_selector.select_option(label=settings.role_label)
    except Exception:
        role_selector.select_option(settings.role_value)

    # Esperar la condicion real: el menu ya disponible.
    page.get_by_role(
        "link", name=accent_tolerant_pattern("Gestion de Tiempos")
    ).wait_for(timeout=30_000)
```

Si quitas `networkidle`, elimina tambien `TimeoutError` del import de
`sofia_bots/sofia.py`, porque deja de usarse:

```python
from playwright.sync_api import Frame, Page
```

### 3. Arranque mas rapido de Chromium

En `sofia_bots/browser.py`, metodo `BrowserSession.start`:

```python
self.browser = self.playwright.chromium.launch(
    headless=self.settings.headless,
    slow_mo=self.settings.slow_mo,
    args=[
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--no-default-browser-check",
        "--no-first-run",
    ],
)
```

### 4. Opcional: esperar el campo del formulario

En `sofia_bots/sofia.py`, funcion `content_frame`, se puede esperar el campo real
en vez del `body` del iframe:

```python
def content_frame(page):
    frame = page.frame_locator('iframe[name="contenido"]')
    frame.locator("#fechaInicioEvento").wait_for(timeout=30_000)
    return frame
```

### 5. Opcional: reducir el sondeo del login

En `sofia_bots/sofia.py`, funcion `find_login_frame`:

```python
poll_ms = 250
```

### Como medir el cambio

Agrega tiempos temporales en `bootstrap_sofia` y compara varias ejecuciones
antes y despues, a la misma hora:

```python
import time

t0 = time.perf_counter()
login(page, settings)
print(f"[tiempo] login: {time.perf_counter() - t0:.2f}s")

t1 = time.perf_counter()
select_role(page, settings)
print(f"[tiempo] rol: {time.perf_counter() - t1:.2f}s")

t2 = time.perf_counter()
open_menu_path(page, *module_path)
print(f"[tiempo] menu: {time.perf_counter() - t2:.2f}s")
```

### Recomendaciones

- No reemplazar esperas por `time.sleep()`: se rompe cuando Sofia responde distinto.
- No bajar a la ligera los timeouts de 30 s o 120 s; en horas pico el portal tarda.
- `headless` puede ser mas rapido, pero Sofia puede requerir navegador visible.
- No bloquear imagenes, CSS o JavaScript: puede romper el portal.
- Reutilizar cookies o sesion ahorraria el login, pero cambia el modelo de
  seguridad y debe evaluarse aparte.
- Si se modifica el codigo, recompilar el ejecutable con
  `crear_ejecutable_sofiabot.bat`. El lanzador programado usa `.venv` y toma los
  cambios sin recompilar.

## Dashboard de pruebas

El proyecto incluye un generador de dashboard que ejecuta las pruebas y deja un
reporte visual autocontenido:

```powershell
python tools/generar_dashboard_pruebas.py
```

Salidas:

```text
reportes\dashboard_pruebas.html
reportes\resultados_pruebas.json
```

El dashboard muestra:

- Resumen de pruebas aprobadas, fallidas, errores y omitidas.
- Detalle por suite con descripcion, estado y duracion de cada prueba.
- Rama, commit, version de Python y fecha de la corrida.
- Chequeos de compilacion e importacion del limpiador.

Incluye las pruebas de integracion del bot y el limpiador (credenciales,
carpeta de salida, errores fatales y limpieza del archivo) y las 7 pruebas FSM
originales. El HTML no usa CDN ni servidor: se abre directamente en el navegador.
El JSON se puede consumir desde Power BI si se quiere otro tablero.

## Programador de tareas de Windows

### Actualizacion diaria a la 1:00 p.m.

La forma recomendada es el flujo de Power Automate descrito en
`power_automate\LEEME.md`. Si prefieres el Programador de tareas de Windows,
crea una tarea diaria a las 13:00 con:

- Programa: `C:\Users\capatino\Documents\Software con códex\ejecutar_inasistencias_programada.bat`
- Argumentos: dejar vacio
- Iniciar en: `C:\Users\capatino\Documents\Software con códex`

Ese lanzador no abre cuadros de credenciales: usa las claves guardadas en
`.env`. Deja el equipo encendido y con sesion iniciada.

### Ejecutar y suspender el equipo al finalizar

Usa este lanzador:

- Programa: `C:\Users\capatino\Documents\Software con códex\ejecutar_inasistencias_y_suspender.bat`
- Argumentos: dejar vacio
- Iniciar en: `C:\Users\capatino\Documents\Software con códex`

En la tarea programada activa:

- `Ejecutar solo si el usuario inicio sesion`, recomendado mientras Sofia Plus requiera navegador visible.
- `Reactivar el equipo para ejecutar esta tarea`, en la pestaña Condiciones.
- `Iniciar la tarea solo si el equipo esta conectado a corriente alterna`, si aplica.

Para que Windows permita despertar desde suspension, revisa tambien:

```powershell
powercfg /waketimers
powercfg /devicequery wake_armed
```

### Forma manual, llamando Python directamente

- Programa: `C:\Users\capatino\Documents\Software con códex\.venv\Scripts\python.exe`
- Argumentos: `-m bots.descargar_inasistencias --headless --reintentos-servidor 120 --espera-servidor 60`
- Iniciar en: `C:\Users\capatino\Documents\Software con códex`

Antes de crear la tarea, deja listo el archivo `.env` en la raiz del proyecto o define las variables persistentes con `setx`.

## Programas en Python para oficina

Tambien queda disponible un modulo con utilidades generales para oficina:

- Unir varios archivos Excel o CSV.
- Limpiar filas vacias y duplicadas.
- Separar cada hoja de un Excel en archivos independientes.
- Organizar archivos por tipo.
- Renombrar archivos con prefijo y numeracion.

Ver comandos disponibles:

```powershell
python -m programas_oficina.oficina --help
```

### Unir varios Excel

```powershell
python -m programas_oficina.oficina unir-excel "C:\Ruta\Reportes" --patron "*.xlsx" --salida "C:\Ruta\Reporte_unido.xlsx"
```

Para unir CSV:

```powershell
python -m programas_oficina.oficina unir-excel "C:\Ruta\Reportes" --patron "*.csv" --salida "C:\Ruta\Reporte_unido.xlsx"
```

### Limpiar un Excel o CSV

```powershell
python -m programas_oficina.oficina limpiar-excel "C:\Ruta\archivo.xlsx" --salida "C:\Ruta\archivo_limpio.xlsx"
```

### Separar hojas de un Excel

```powershell
python -m programas_oficina.oficina separar-hojas "C:\Ruta\archivo.xlsx" --salida "C:\Ruta\Hojas"
```

### Organizar archivos por tipo

Por seguridad, el comando copia los archivos. Para moverlos, agrega `--mover`.

```powershell
python -m programas_oficina.oficina organizar-archivos "C:\Ruta\Descargas"
```

### Renombrar archivos

```powershell
python -m programas_oficina.oficina renombrar-archivos "C:\Ruta\Facturas" --prefijo factura --patron "*.pdf"
```

### Renumerar PDF del primer trimestre

Primero revisa la vista previa:

```powershell
python -m programas_oficina.oficina renumerar-pdf
```

Para renombrar realmente los archivos:

```powershell
python -m programas_oficina.oficina renumerar-pdf --aplicar
```

Tambien puedes ejecutar:

```powershell
renumerar_pdfs_primer_trimestre.bat
```
