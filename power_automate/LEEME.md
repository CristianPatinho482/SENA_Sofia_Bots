# Power Automate del reporte de inasistencias

En esta carpeta estan las dos plantillas de flujo:

| Archivo | Uso |
| --- | --- |
| `flujo_1_boton_powerbi.json` | Se dispara con el boton del reporte de Power BI. Ejecuta el bot interactivo y pide credenciales solo la primera vez. |
| `flujo_2_programado_1300.json` | Se ejecuta todos los dias a la 1:00 p.m. (hora Colombia) con el lanzador autonomo. |

Los archivos son plantillas de definicion, no paquetes `.zip` importables. Se
crean una vez en Power Automate y luego se pega/adapta el contenido, o se usan
como guia con los pasos de abajo. La razon es que cada entorno tiene sus propias
conexiones, maquina y flujo de escritorio; un paquete con IDs ajenos suele
fallar al importar.

## Antes de empezar

1. El proyecto debe estar en la maquina donde se ejecuta Power Automate Desktop.
2. Debe existir el entorno virtual `.venv` o Python disponible en el `PATH`.
3. La primera vez, ejecuta manualmente:

   ```powershell
   ejecutar_inasistencias.bat
   ```

   Ingresa usuario y contrasena cuando el bot lo pida. Eso crea/actualiza
   `.env` y crea la carpeta `<Escritorio>\Inasistencias`.

4. Verifica en Power Automate que tengas las conexiones:
   - **Power BI** (`shared_powerbi`)
   - **Desktop flows** (`shared_uiflow`)

## Flujo de escritorio (se crea una sola vez)

En Power Automate Desktop crea dos flujos de escritorio:

### 1. `SOFIABOT - Inasistencias interactivo`

Acciones:

1. **Ejecutar aplicacion**
   - Ruta: `C:\Users\capatino\Documents\Software con códex\ejecutar_inasistencias.bat`
   - Directorio de trabajo: `C:\Users\capatino\Documents\Software con códex`
   - Esperar a que termine: **Si**
2. (Opcional) **Si** el codigo de salida es distinto de 0, registrar un error.

### 2. `SOFIABOT - Inasistencias programado`

Acciones:

1. **Ejecutar aplicacion**
   - Ruta: `C:\Users\capatino\Documents\Software con códex\ejecutar_inasistencias_programada.bat`
   - Directorio de trabajo: `C:\Users\capatino\Documents\Software con códex`
   - Esperar a que termine: **Si**
2. (Opcional) **Si** el codigo de salida es distinto de 0, registrar un error.

> El lanzador programado escribe un log en `logs\inasistencias_programada_AAAAMMDD.log`.
> No abre el cuadro de credenciales: si `.env` no existe o esta incompleto,
> termina con error. Por eso la primera ejecucion se hace con el boton o con el
> `.bat` interactivo.

## Flujo 1: boton de Power BI

1. En Power Automate, **Crear > Flujo de nube automatizado**.
2. Busca el desencadenador **Cuando se pulsa un boton de Power BI**
   (*On Power BI button clicked*).
3. Agrega la accion **Ejecutar un flujo creado con Power Automate for desktop**
   y selecciona `SOFIABOT - Inasistencias interactivo`.
4. Modo de ejecucion: **Con sesion iniciada (attended)**.
5. Guarda el flujo con el nombre `SOFIABOT - Descargar inasistencias (boton Power BI)`.
6. En Power BI Desktop:
   - Abre el `.pbix`.
   - Inserta un **boton** o un visual **Power Automate**.
   - En la accion del boton elige **Power Automate** y selecciona este flujo.
   - Agrega un texto junto al boton:

     > **Actualizar inasistencias**
     > Presiona este boton solo la primera vez. Despues la actualizacion es
     > automatica todos los dias a la 1:00 p.m. Vuelve a presionarlo unicamente
     > si Sofia Plus te pide cambiar la contrasena.

7. Publica el reporte en el servicio de Power BI.

> Si prefieres pegar la definicion: abre el flujo, usa **Peek code** y reemplaza
> el objeto `definition` por el de `flujo_1_boton_powerbi.json`. Ajusta
> `DesktopFlowId` al ID real del flujo de escritorio.

## Flujo 2: actualizacion diaria a la 1:00 p.m.

1. **Crear > Flujo de nube programado**.
2. Frecuencia: **Dia**, intervalo **1**, zona horaria
   **SA Pacific Standard Time** (Colombia), hora **13:00**.
3. Agrega la accion **Ejecutar un flujo creado con Power Automate for desktop**
   y selecciona `SOFIABOT - Inasistencias programado`.
4. Modo de ejecucion: **Sin atender (unattended)** si la maquina esta
   configurada como maquina de Power Automate; si no, usa **attended** y deja la
   sesion de Windows abierta.
5. Guarda como `SOFIABOT - Inasistencias diario 13:00`.

> Power Automate no ejecuta archivos locales directamente: siempre lo hace a
> traves de un flujo de escritorio en una maquina registrada. Si no tienes
> maquina unattended, la alternativa es el Programador de tareas de Windows con
> `ejecutar_inasistencias_programada.bat`.

## Que hace el bot

1. Reutiliza las credenciales de `.env`.
2. Si no existen (o Sofia Plus las rechaza), abre el cuadro y las guarda.
3. Crea `<Escritorio>\Inasistencias` si no existe.
4. Descarga el consolidado y lo guarda como `Inasistencias.xls`.
5. Ejecuta el limpiador FSM y reemplaza el mismo archivo.
6. Power BI lee ese archivo y muestra los datos actualizados.

## Solucion de problemas

- **No aparece el boton en Power BI:** el visual Power Automate necesita que el
  flujo exista y que el reporte se haya publicado con la conexion correcta.
- **El flujo programado falla:** revisa `logs\inasistencias_programada_*.log`.
- **Sofia Plus pide cambiar la contrasena:** ejecuta el boton interactivo,
  ingresa la clave nueva y se guardara en `.env`.
- **La maquina estaba apagada a la 1:00 p.m.:** Power Automate no ejecuta el
  flujo hasta que la maquina este disponible si es unattended. Programa el
  equipo para que no se suspenda.
