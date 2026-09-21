import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const outputDir = "C:/Users/capatino/Documents/Software con códex/astin_normalizer/outputs/normalizacion_estricta_mayo_2026";
const outputPath = `${outputDir}/ASTIN_Modelo_Estrella.xlsx`;
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const dimensionIds = {
  center: new Set(workbook.worksheets.getItem("DimCentro").getUsedRange().values.slice(1).map((row) => row[0])),
  period: new Set(workbook.worksheets.getItem("DimPeriodo").getUsedRange().values.slice(1).map((row) => row[0])),
  category: new Set(workbook.worksheets.getItem("DimCategoria").getUsedRange().values.slice(1).map((row) => row[0])),
  indicator: new Set(workbook.worksheets.getItem("DimIndicador").getUsedRange().values.slice(1).map((row) => row[0])),
};
const factRows = workbook.worksheets.getItem("FactMetas").getUsedRange().values.slice(1);
const invalidForeignKeys = factRows.filter((row) => !dimensionIds.center.has(row[0]) || !dimensionIds.period.has(row[1]) || !dimensionIds.category.has(row[2]) || !dimensionIds.indicator.has(row[3]));
if (invalidForeignKeys.length) throw new Error(`Se detectaron ${invalidForeignKeys.length} claves foráneas inválidas.`);
const summary = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 5000, tableMaxRows: 5, tableMaxCols: 8 });
const facts = await workbook.inspect({ kind: "table", range: "FactMetas!A1:G12", maxChars: 3000, tableMaxRows: 12, tableMaxCols: 7 });
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, summary: "formula error scan" });
await fs.writeFile(`${outputDir}/verification-summary.ndjson`, `${summary.ndjson}\n${facts.ndjson}\n${errors.ndjson}`);
for (const name of ["DimCentro", "DimPeriodo", "DimCategoria", "DimIndicador", "FactMetas"]) {
  const image = await workbook.render({ sheetName: name, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${outputDir}/verify-${name}.png`, new Uint8Array(await image.arrayBuffer()));
}
console.log(await fs.readFile(`${outputDir}/verification-summary.ndjson`, "utf8"));
