# Power Automate del reporte de inasistencias

Esta carpeta contiene las definiciones de referencia de los dos flujos. La guia
completa (requisitos, conexiones, flujos de escritorio, creacion de cada flujo y
solucion de problemas) esta consolidada en:

```text
README.md > Integracion con Power BI y Power Automate
```

Archivos:

| Archivo | Uso |
| --- | --- |
| `flujo_1_boton_powerbi.json` | Se dispara con el boton del reporte de Power BI. Ejecuta el bot interactivo y pide credenciales solo la primera vez. |
| `flujo_2_programado_1300.json` | Se ejecuta todos los dias a la 1:00 p.m. (hora Colombia) con el lanzador autonomo. |

No son paquetes `.zip` importables: cada entorno tiene sus propias conexiones,
maquina y flujo de escritorio, y un paquete con IDs ajenos suele fallar al
importar. Usalos como referencia o pega su `definition` desde **Peek code**
ajustando `DesktopFlowId`.
