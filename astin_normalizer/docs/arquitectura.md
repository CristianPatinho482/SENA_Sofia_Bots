# Arquitectura del MVP

```mermaid
flowchart LR
    A[Libro Excel] --> B[ExcelReader]
    L[Modelo de referencia] --> M[BusinessModelInferencer]
    B --> C[StructureAnalyzer]
    C --> D[HierarchyParser]
    D --> E[AtomicRecordDetector]
    E --> F[Normalizer]
    F --> G[DimensionBuilder]
    F --> H[FactBuilder]
    G --> I[Validator]
    H --> I
    M --> I
    I --> J[ExcelExporter]
    J --> K[ASTIN_Modelo_Estrella.xlsx]
```

Cada componente tiene una única responsabilidad. `NormalizationPipeline` sólo orquesta el flujo y la interfaz Tkinter sólo recoge acciones del usuario y presenta su resultado.
