# Bots Sofia Plus

Base modular para bots de Sena Sofia Plus.

## Modulos creados

- `sofia_bots/settings.py`: configuracion, credenciales por variables de entorno y carpetas.
- `sofia_bots/browser.py`: sesion Playwright con reinicio automatico y reintentos.
- `sofia_bots/sofia.py`: login, seleccion de rol, apertura de rutas de menu y validacion basica de sesion.
- `sofia_bots/downloads.py`: descargas con `expect_download`, nombres unicos y opcion de sobrescritura.
- `sofia_bots/control.py`: bitacora Excel para evitar duplicados y registrar errores.
- `sofia_bots/inasistencias_cleaner.py`: limpieza FSM del consolidado y salida lista para Power BI.
- `sofia_bots/multi.py`: utilidad simple para repartir tareas entre varios bots/hilos.
- `bots/descargar_inasistencias.py`: primer bot modular para descargar el consolidado de inasistencias.

## Credenciales

Ejecuta exactamente esto (en orden):

cd "C:\Users\capatino\Documents\Software con códex"


El nuevo bot no deja usuario ni clave escritos dentro del codigo. Puedes configurarlas de dos formas.

### Opcion recomendada: archivo .env

Copia `.env.example` como `.env` en la raiz del proyecto:

```text
C:\Users\capatino\Documents\Software con códex\.env
```

Contenido minimo:

```text
SOFIA_USUARIO=tu_documento
SOFIA_PASSWORD=tu_clave
```

Tambien puedes configurar la carpeta sincronizada de SharePoint/Teams:

```text
INASISTENCIAS_SALIDA=C:\Users\capatino\OneDrive - Servicio Nacional de Aprendizaje\Equipo ASTIN-DESAROLLOS POWER-BI - RAPS ASTIN 2026
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

### Con cuadro de credenciales

Para uso manual desde un icono de escritorio o desde el lanzador:

```powershell
ejecutar_inasistencias.bat
```

Ese lanzador muestra un cuadro para ingresar usuario y contrasena. Las credenciales se usan solo durante esa ejecucion y no se escriben en `.env`.

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

Nota: el ejecutable usa el cuadro de credenciales, por lo que no guarda usuario ni contrasena. En otros equipos debe existir Microsoft Excel y Playwright/Chromium debe poder ejecutarse correctamente.

La version completa incluye Chromium dentro del `.exe`, por eso pesa mas y puede tardar unos segundos en abrir la primera vez.

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

Este bot actualiza siempre el archivo:

```text
C:\Users\capatino\OneDrive - Servicio Nacional de Aprendizaje\Equipo ASTIN-DESAROLLOS POWER-BI - RAPS ASTIN 2026\Inasistencias.xls
```

Si ya existe, lo reemplaza. Esto permite programarlo diariamente en el Programador de tareas de Windows.

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

## Programador de tareas de Windows

### Ejecutar y dejar el equipo encendido

Forma recomendada para uso manual con cuadro de credenciales:

- Programa: `C:\Users\capatino\Documents\Software con códex\ejecutar_inasistencias.bat`
- Argumentos: dejar vacio
- Iniciar en: `C:\Users\capatino\Documents\Software con códex`

Para una tarea completamente automatica, usa el comando sin cuadro de credenciales y deja credenciales actualizadas en `.env`.

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
