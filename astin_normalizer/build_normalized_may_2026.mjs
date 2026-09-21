import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const sourcePath = "C:/Users/capatino/Desktop/Metas de formación/METAS CENTRO ASTIN - CORTE 31 MAYO 2026.xlsx";
const referencePath = "C:/Users/capatino/Desktop/Metas de formación/Metas al 31 de mayo de 2026/Modelo_Normalizado_Metas_Centro_ASTIN_Mayo2026.xlsx";
const outputDir = "C:/Users/capatino/Documents/Software con códex/astin_normalizer/outputs/normalizacion_estricta_mayo_2026";
const outputPath = `${outputDir}/ASTIN_Modelo_Estrella.xlsx`;

const isMojibake = (text) => /Ã|Â|â/.test(text);
const cleanText = (value) => {
  if (typeof value !== "string") return value;
  const repaired = isMojibake(value) ? Buffer.from(value, "latin1").toString("utf8") : value;
  return repaired.replace(/\s+/g, " ").trim();
};

const toNumber = (value) => {
  if (value === null || value === undefined || value === "-") return null;
  if (typeof value === "number") return value;
  const text = cleanText(String(value)).replace(/%$/, "").replace(/,/g, "");
  const number = Number(text);
  if (Number.isNaN(number)) return value;
  return String(value).includes("%") ? number / 100 : number;
};

let categoryIdByLabel = new Map();
const getCategoryId = (section, indicator) => {
  const text = `${section} ${indicator}`.toLowerCase();
  if (section.includes("Certificación de Competencias")) return categoryIdByLabel.get("Certificación De Competencias Laborales");
  if (section.includes("Desagregación")) return categoryIdByLabel.get("Desagregación Otras Poblaciones Vulnerables");
  if (section.includes("Poblaciones Vulnerables")) return categoryIdByLabel.get("Poblaciones Vulnerables");
  if (section.includes("Emprendimiento")) return categoryIdByLabel.get("Emprendimiento Y Fortalecimiento");
  if (section.includes("Contratos")) return categoryIdByLabel.get("Contratos De Aprendizaje");
  if (text.includes("articulación")) return categoryIdByLabel.get("Articulación con la Media");
  if (text.includes("campesena")) return categoryIdByLabel.get("CampeSENA");
  if (text.includes(" fic") || text.includes(" f.i.c")) return categoryIdByLabel.get("FIC");
  if (text.includes("full popular") || text.includes("especial popular")) return categoryIdByLabel.get("Full Popular");
  return categoryIdByLabel.get("Formación regular");
};

const isAggregation = (indicator) => /(?:^|\b)total(?:es)?\b/i.test(indicator) || /=\s*\(/.test(indicator);
const isHeader = (meta, execution) => String(cleanText(meta)).toLowerCase() === "meta" && String(cleanText(execution)).toLowerCase().includes("ejecución");

const sourceBook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
const sourceRows = sourceBook.worksheets.getItemAt(0).getUsedRange().values;
const referenceBook = await SpreadsheetFile.importXlsx(await FileBlob.load(referencePath));
const centerRows = referenceBook.worksheets.getItem("DimCentro").getUsedRange().values;
const periodRows = referenceBook.worksheets.getItem("DimPeriodo").getUsedRange().values;
const categoryRows = referenceBook.worksheets.getItem("DimCategoria").getUsedRange().values;
const referenceHeaders = {
  center: centerRows[0].map(cleanText),
  period: periodRows[0].map(cleanText),
  category: categoryRows[0].map(cleanText),
  indicator: referenceBook.worksheets.getItem("DimIndicador").getUsedRange().values[0].map(cleanText),
  fact: referenceBook.worksheets.getItem("FactMetas").getUsedRange().values[0].map(cleanText),
};
const categories = categoryRows.slice(1).map((row) => row.map(cleanText));
categoryIdByLabel = new Map(categories.map(([id, label]) => [label, id]));

let currentSection = "";
const records = [];
const removed = [];
for (const row of sourceRows) {
  // El rango usado comienza en la columna B; Artifact Tool entrega ese rango sin la columna A vacía.
  const indicator = cleanText(row[0]);
  const meta = cleanText(row[1]);
  const execution = cleanText(row[2]);
  const percentage = cleanText(row[3]);
  if (!indicator) continue;
  if (isHeader(meta, execution)) {
    currentSection = indicator;
    continue;
  }
  if (meta === null && execution === null && percentage === null) continue;
  if (isAggregation(indicator)) {
    removed.push(indicator);
    continue;
  }
  records.push({
    indicator,
    categoryId: getCategoryId(currentSection, indicator),
    meta: toNumber(meta),
    execution: toNumber(execution),
    executionIsPercentage: typeof execution === "string" && execution.includes("%"),
    percentage: toNumber(percentage),
  });
}

const indicators = records.map((record, index) => [index + 1, record.indicator]);
const center = centerRows[1].map(cleanText);
const period = periodRows[1].map(cleanText);
const fact = records.map((record, index) => [
  center[0], period[0], record.categoryId, index + 1,
  record.meta, record.execution, record.percentage,
]);

const workbook = Workbook.create();
const headerStyle = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center" };
const bodyBorder = { preset: "insideHorizontal", style: "thin", color: "#D9E2F3" };

function addSheet(name, headers, values, widths, formats = {}) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  sheet.getRangeByIndexes(0, 0, 1, headers.length).values = [headers];
  if (values.length) sheet.getRangeByIndexes(1, 0, values.length, headers.length).values = values;
  const range = sheet.getRangeByIndexes(0, 0, Math.max(values.length + 1, 2), headers.length);
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format = headerStyle;
  range.format.borders = bodyBorder;
  sheet.freezePanes.freezeRows(1);
  for (let index = 0; index < widths.length; index += 1) sheet.getRangeByIndexes(0, index, 1, 1).format.columnWidth = widths[index];
  for (const [address, format] of Object.entries(formats)) sheet.getRange(address).format.numberFormat = format;
  sheet.tables.add(sheet.getRangeByIndexes(0, 0, values.length + 1, headers.length), true, `${name}Table`);
  return sheet;
}

addSheet("DimCentro", referenceHeaders.center, [center], [12, 16, 65, 16]);
addSheet("DimPeriodo", referenceHeaders.period, [[period[0], period[1], period[2], new Date(`${period[3]}T00:00:00`)]], [14, 12, 16, 16], { "D2:D2": "yyyy-mm-dd" });
addSheet("DimCategoria", referenceHeaders.category, categories, [14, 48]);
addSheet("DimIndicador", referenceHeaders.indicator, indicators, [14, 100]);
const factSheet = addSheet("FactMetas", referenceHeaders.fact, fact, [12, 14, 14, 14, 14, 14, 14], {
  "E2:F84": "#,##0.00;[Red]-#,##0.00",
  "G2:G84": "0.00%",
});
records.forEach((record, index) => {
  if (record.executionIsPercentage) factSheet.getRangeByIndexes(index + 1, 5, 1, 1).format.numberFormat = "0.00%";
});

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, retained: records.length, removed: removed.length, removed }, null, 2));
