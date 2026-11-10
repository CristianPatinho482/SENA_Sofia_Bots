# Ajuste del reporte de Power BI

La guia consolidada (pasos para cambiar el origen, agregar el boton y publicar)
esta en:

```text
README.md > Integracion con Power BI y Power Automate > Ajustar el .pbix
```

Archivos de referencia:

- `consulta_inasistencias.pq`: consulta M lista para pegar en el Editor avanzado.
- Reporte destino: `Reporte personalizado inasistencias Sofía v2.pbix`.

Recordatorio clave: el archivo limpio del bot ya trae **una sola fila de
encabezados**; no apliques `Table.Skip(1)`.

El bot deja el archivo en:

```text
<Escritorio>\Inasistencias\Inasistencias.xls
```
