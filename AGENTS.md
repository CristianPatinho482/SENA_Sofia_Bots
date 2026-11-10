# AGENTS.md

Guia operativa para agentes de IA que trabajen en este repositorio.

## Proposito

Automatizar la descarga, limpieza y publicacion del **Consolidado de
Inasistencias** de SENA Sofia Plus para el reporte de Power BI "Reporte
personalizado inasistencias Sofia v2".

Flujo de extremo a extremo:

```text
Power BI (boton / Power Automate)
  -> bot interactivo (solo primera vez o cambio de clave)
  -> Power Automate Desktop ejecuta el .bat
  -> Playwright navega Sofia Plus y descarga Inasistencias.xls
  -> limpiador FSM deja 10 columnas limpias
  -> <Escritorio>\Inasistencias\Inasistencias.xls
  -> Power BI lee ese archivo
```

La actualizacion diaria de las 13:00 se ejecuta con
`ejecutar_inasistencias_programada.bat` desde Power Automate o el Programador de
tareas de Windows.

## Comandos utiles

```powershell
# Instalar dependencias
python -m pip install -r requirements.txt

# Bot interactivo (pide credenciales solo si faltan)
python -m bots.sofiabot_inasistencias_app

# Bot sin interfaz grafica (usa .env)
python -m bots.descargar_inasistencias

# Forzar actualizacion de credenciales
python -m bots.descargar_inasistencias --pedir-credenciales --forzar-credenciales

# Limpiar un archivo ya descargado
python -m sofia_bots.inasistencias_cleaner "C:\Ruta\Inasistencias.xls"

# Pruebas
python -m unittest discover -s tests -v
Push-Location "Proyecto Limpiador Inasistencias"
..\.venv\Scripts\python.exe -m unittest test_fsm_inasistencias -v
Pop-Location

# Dashboard de pruebas
python tools/generar_dashboard_pruebas.py

# Recompilar ejecutable (solo si cambia codigo que va al .exe)
crear_ejecutable_sofiabot.bat
```

## Arquitectura

```text
bots/
  descargar_inasistencias.py      Orquestador: credenciales, descarga, limpieza.
  sofiabot_inasistencias_app.py   Entrada grafica (Tk) del boton.

sofia_bots/
  settings.py               Rutas, .env, credenciales y Escritorio real.
  credential_store.py       Guarda/lee credenciales en .env de forma atomica.
  credentials_dialog.py     Cuadro Tk de usuario/contrasena.
  sofia.py                  Login, seleccion de rol y menu de Sofia Plus.
  browser.py                Playwright + reinicio de sesion.
  downloads.py              Guardado de descargas.
  excel_tools.py            Renombra la hoja a "Inasistencias".
  inasistencias_cleaner.py  Limpiador FSM integrado (10 columnas).
  control.py                Log de control en Excel.
  power.py                  Suspension de Windows.

power_automate/             Plantillas de los dos flujos.
power_bi/                   Consulta M para el .pbix.
tests/                      Pruebas de integracion del limpiador.
reportes/                   Dashboard HTML/JSON generado.
```

## Contrato de datos

Salida del limpiador, en este orden:

```text
Instructor, Ficha, Programa, Apellidos, Nombres,
Identificacion Aprendiz, Fecha Inicio, Fecha Fin, Cant.horas, Justificacion
```

- El archivo se llama siempre `Inasistencias.xls` y se reemplaza de forma atomica.
- Tiene contenido XLSX aunque la extension sea `.xls`; `Excel.Workbook` lo detecta.
- La hoja se llama `Inasistencias`.
- Ya trae una sola fila de encabezados: **no** aplicar `Table.Skip(1)` en Power Query.
- La limpieza es idempotente: si el esquema ya es el limpio, no se reprocesa.

## Credenciales y seguridad

- Se guardan en `.env` (`SOFIA_USUARIO`, `SOFIA_PASSWORD`). `.env` esta en `.gitignore`.
- La contrasena nunca se imprime en consola ni en logs.
- El bot interactivo pide credenciales solo si faltan o si Sofia Plus rechaza el
  ingreso (por ejemplo, cambio obligatorio de contrasena).
- El lanzador programado nunca abre dialogos: si no hay credenciales, falla con
  mensaje claro.
- No subir `.env`, archivos `*.xls`, `dist/`, `build/` ni `node_modules/`.

## Rutas operativas

- Salida por defecto: `<Escritorio>\Inasistencias\Inasistencias.xls`
  (se detecta el Escritorio real desde el registro de Windows; respeta OneDrive).
- Se puede sobrescribir con `--salida` o con `INASISTENCIAS_SALIDA` en `.env`.
- El log del lanzador programado queda en `logs\inasistencias_programada_AAAAMMDD.log`.
- El bot grafico escribe diagnostico en `logs\sofiabot_app.log`.
- Si el `.exe` esta dentro de `dist`, reutiliza el `.env` y `logs` de la raiz
  del proyecto. Si se copia fuera del proyecto, usa su propia carpeta.
- El archivo de control queda en la carpeta de salida como `control_inasistencias.xlsx`.

## Reglas para cambios

- No romper la ruta ni el nombre que consume Power BI: `Inasistencias.xls`.
- La limpieza es obligatoria; si falla, el bot no debe reportar exito ni borrar
  el archivo original.
- Mantener la escritura atomica del limpiador.
- No reemplazar esperas de Playwright por `time.sleep()`.
- No bajar timeouts de 30/120 s sin medir en hora pico.
- Al cambiar el codigo que va al ejecutable, recompilar con
  `crear_ejecutable_sofiabot.bat`; el lanzador programado usa `.venv` y toma los
  cambios sin recompilar.
- Ejecutar las pruebas y el dashboard antes de commitear.
- El `git status` tiene ruido de `astin_normalizer/node_modules/`; agregar solo
  archivos explicitos, nunca `git add .`.

## Documentacion relacionada

- `README.md`: uso, limpieza, dashboard y ajustes de navegacion.
- `power_automate/LEEME.md`: como crear los dos flujos.
- `power_bi/consulta_inasistencias.pq`: consulta M para el reporte.
- `reportes/dashboard_pruebas.html`: ultimo resultado visual de pruebas.

## Recomendaciones de arquitectura (pendientes, no implementadas)

Fuente: `Arquitectura de Sena Sofia Bots.docx`. El archivo recibido esta
truncado (1.428 caracteres); solo alcanza a cubrir credenciales y el inicio de
rutas dinamicas. Pedir el documento completo antes de evaluar el resto.

### 1. Guardar la contrasena con el Administrador de Credenciales de Windows

- Situacion actual: `SOFIA_PASSWORD` queda en texto plano dentro de `.env`.
  Funciona y esta ignorado por Git, pero cualquier proceso del usuario puede
  leerlo.
- Propuesta: usar `keyring` (backend `Windows Credential Locker`) o DPAPI via
  `win32crypt.CryptProtectData`. La contrasena deja de existir en disco en claro.
- Aplicabilidad: alta. Es el cambio de mayor valor de seguridad y no afecta la
  ruta ni el contrato de datos.
- Restricciones a considerar antes de implementar:
  - El `.exe` con PyInstaller debe incluir los backends de `keyring`
    (`--hidden-import keyring.backends.Windows`) o la dependencia fallara en
    tiempo de ejecucion.
  - Las credenciales de Windows son por usuario: el flujo programado de Power
    Automate debe ejecutarse con la misma cuenta que guardo la clave.
  - Hace falta migracion: leer primero `keyring`, luego `.env`; si encuentra la
    clave en `.env`, moverla al Credential Manager y borrarla del archivo.
  - Mantener `SOFIA_USUARIO` en `.env` (el usuario no es secreto) simplifica el
    diagnostico.

### 2. Distinguir contrasena caducada, credenciales invalidas y cuenta bloqueada

- Situacion actual: `login()` lanza `SofiaLoginError` ante cualquier fallo y el
  modo interactivo permite hasta 3 intentos con credenciales nuevas. No se lee
  el mensaje real del portal, asi que no se distingue el motivo.
- Propuesta: extraer el texto de error que muestra Sofia Plus y clasificarlo:
  - `credenciales_invalidas`: no reintentar en automatico; pedir de nuevo solo
    en modo interactivo.
  - `contrasena_caducada`: detener el flujo y avisar que debe cambiarla en el
    portal; el bot no puede automatizar ese cambio.
  - `cuenta_bloqueada`: detener de inmediato y no reintentar, para no agravar el
    bloqueo.
- Aplicabilidad: alta. Hoy un bucle de reintentos podria contribuir a bloquear
  la cuenta. El lanzador programado ya falla rapido, pero el interactivo no
  distingue causas.
- Restricciones: los textos del portal pueden cambiar; conviene una lista de
  patrones tolerantes a tildes y mayusculas, y dejar el texto original en el log.

### 3. Rutas dinamicas y compatibles con OneDrive

- Situacion actual: el Escritorio se detecta desde el registro y el limpiador
  reemplaza el archivo de forma atomica; `INASISTENCIAS_SALIDA` permite
  sobrescribir la carpeta.
- Propuesta del documento: no fijar rutas absolutas y respetar redirecciones de
  OneDrive.
- Aplicabilidad: ya implementado en lo esencial. Pendiente menor: usar
  `Path.resolve()` al comparar rutas y documentar el caso en que OneDrive deja
  el archivo en estado "solo en linea" (puede retrasar la lectura de Power BI).
