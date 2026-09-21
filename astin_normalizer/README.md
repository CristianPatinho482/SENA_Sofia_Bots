# ASTIN Data Platform — Normalizador Inteligente de Metas Institucionales

Aplicación de escritorio para convertir libros de metas institucionales con estructura jerárquica en un modelo estrella para Power BI.

## Uso

1. Instale dependencias: `pip install -r requirements.txt`.
2. Ejecute: `python main.py`.
3. Seleccione el libro de origen, opcionalmente el modelo Excel de referencia y la carpeta de salida.

El resultado se guarda como `ASTIN_Modelo_Estrella.xlsx`, sin alterar el archivo de origen.

## Normalización PE-04

El módulo `pe04` crea `FactPE04` al nivel de ficha/curso y utiliza `DimCentro` y `DimPeriodo` de un `ASTIN_Modelo_Estrella.xlsx`; así ambos modelos se relacionan en Power BI sin mezclar sus granularidades.

```powershell
python normalizar_pe04.py "C:\ruta\PE-04_mayo.xlsx" "C:\ruta\ASTIN_Modelo_Estrella.xlsx" "C:\ruta\salida"
```

## Arquitectura

```
ExcelReader → StructureAnalyzer → HierarchyParser → AtomicRecordDetector
    → Normalizer → DimensionBuilder / FactBuilder → Validator → ExcelExporter
```

Las reglas de clasificación y los alias de columnas se encuentran en `rules.json`; pueden ampliarse sin editar código. El libro de referencia se utiliza sólo para inferir y validar el contrato de tablas y columnas; sus datos no se copian.

La validación compara FactMetas con el mayor total explícito detectado en el origen. Si el formato usa varios totales de diferente granularidad, el informe lo marca para revisión y las reglas se pueden ajustar en `rules.json`.

## Limitación inicial

El detector es deliberadamente conservador: conserva filas con medida numérica y descarta filas de total, fórmulas y encabezados. Un archivo real de ejemplo permitirá calibrar los alias y los niveles jerárquicos específicos de ASTIN.
