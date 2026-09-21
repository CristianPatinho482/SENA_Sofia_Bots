import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = "C:/Users/capatino/Desktop/Metas de formación/METAS CENTRO ASTIN - CORTE 31 MAYO 2026.xlsx";
const referencePath = "C:/Users/capatino/Desktop/Metas de formación/Metas al 31 de mayo de 2026/Modelo_Normalizado_Metas_Centro_ASTIN_Mayo2026.xlsx";
const outputDir = "C:/Users/capatino/Documents/Software con códex/astin_normalizer/inspection";

await fs.mkdir(outputDir, { recursive: true });
for (const [label, path] of [["source", sourcePath], ["reference", referencePath]]) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
  const summary = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 14000, tableMaxRows: 8, tableMaxCols: 18, tableMaxCellChars: 70 });
  await fs.writeFile(`${outputDir}/${label}-summary.ndjson`, summary.ndjson);
  const sheets = await workbook.inspect({ kind: "sheet", include: "id,name" });
  await fs.writeFile(`${outputDir}/${label}-sheets.ndjson`, sheets.ndjson);
  const sheetRows = sheets.ndjson.split("\n").filter(Boolean).map(JSON.parse);
  for (const { name } of sheetRows) {
    const safeName = name.replace(/[^A-Za-z0-9_-]/g, "_");
    const image = await workbook.render({ sheetName: name, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(`${outputDir}/${label}-${safeName}.png`, new Uint8Array(await image.arrayBuffer()));
  }
}
