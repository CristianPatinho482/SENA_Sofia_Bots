// Consulta M para Power BI: archivo limpio de inasistencias.
//
// El bot deja el reporte ya limpio (una sola fila de encabezados) en:
//   C:\Users\<usuario>\Desktop\Inasistencias\Inasistencias.xls
//
// Importante: el archivo tiene contenido XLSX aunque la extension sea .xls.
// Excel.Workbook lo detecta automaticamente. NO uses Table.Skip(1): el
// limpiador ya elimino las filas de titulo del reporte original.
//
// Para usarla en el .pbix:
//   1. Inicio > Transformar datos > Nueva origen > Consulta en blanco.
//   2. Editor avanzado > pega este codigo.
//   3. Ajusta "Ruta" si tu Escritorio esta en otra ubicacion.
//   4. Cerrar y aplicar.
//
// Tambien puedes crear un parametro llamado "RutaInasistencias" y usarlo en
// lugar de la cadena fija para mover el reporte entre equipos.

let
    Ruta = "C:\Users\capatino\Desktop\Inasistencias\Inasistencias.xls",
    Origen = Excel.Workbook(File.Contents(Ruta), null, true),
    Hoja = Origen{[Item = "Inasistencias", Kind = "Sheet"]}[Data],
    Encabezados = Table.PromoteHeaders(Hoja, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(
        Encabezados,
        {
            {"Instructor", type text},
            {"Ficha", Int64.Type},
            {"Programa", type text},
            {"Apellidos", type text},
            {"Nombres", type text},
            {"Identificacion Aprendiz", type text},
            {"Fecha Inicio", type date},
            {"Fecha Fin", type date},
            {"Cant.horas", type number},
            {"Justificacion", type text}
        },
        "es-CO"
    )
in
    Tipos
