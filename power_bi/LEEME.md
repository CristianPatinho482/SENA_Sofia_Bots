# Ajuste del reporte de Power BI

Archivo del reporte:

```text
Reporte personalizado inasistencias Sofía v2.pbix
```

El bot deja el archivo limpio en:

```text
C:\Users\capatino\Desktop\Inasistencias\Inasistencias.xls
```

## 1. Cambiar el origen de datos

1. Abre el `.pbix` en Power BI Desktop.
2. **Inicio > Transformar datos**.
3. Selecciona la consulta de inasistencias (o crea una con
   **Nueva origen > Consulta en blanco**).
4. **Inicio > Editor avanzado**.
5. Pega el contenido de `consulta_inasistencias.pq`.
6. Ajusta la variable `Ruta` si el Escritorio esta en otra ubicacion.
7. **Cerrar y aplicar**.

## 2. Quitar el desplazamiento de encabezados

El reporte original venia con filas de titulo y por eso la consulta hacia:

```m
Table.Skip(1)
```

El archivo que produce el bot ya tiene **una sola fila de encabezados**. Si se
mantiene `Table.Skip(1)`, se pierde la primera fila de datos y los encabezados
quedan corridos. Elimina ese paso.

## 3. Agregar el boton de actualizacion

1. En la vista **Informe**, inserta un **boton** o el visual **Power Automate**.
2. En las propiedades del boton, elige **Accion > Power Automate**.
3. Selecciona el flujo `SOFIABOT - Descargar inasistencias (boton Power BI)`.
4. Agrega un cuadro de texto junto al boton:

   > **Actualizar inasistencias**
   > Presiona este boton solo la primera vez. Despues la actualizacion es
   > automatica todos los dias a la 1:00 p.m. Vuelve a presionarlo unicamente
   > si Sofia Plus te pide cambiar la contrasena.

## 4. Publicar

1. Guarda el `.pbix`.
2. **Publicar** en el area de trabajo de Power BI.
3. Verifica que el flujo de Power Automate quede disponible para los usuarios
   del reporte.

## Nota sobre la actualizacion automatica

Power BI no puede leer el Escritorio de otra maquina. El reporte debe abrirse en
el mismo equipo donde corre el bot, o el archivo debe sincronizarse a una carpeta
compartida. Para el escenario actual (un solo equipo con Power BI Desktop), la
ruta del Escritorio es la correcta.
