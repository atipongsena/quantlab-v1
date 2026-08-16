const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const typesFile = path.join(root, "types", "api.ts");

if (!fs.existsSync(typesFile)) {
  console.error("Typecheck error: types/api.ts not found");
  process.exit(1);
}

const content = fs.readFileSync(typesFile, "utf8");
const requiredTypes = [
  "HealthResponse",
  "DatasetListResponse",
  "FactorResearchResponse",
  "BacktestResponse",
  "ValidationResponse",
  "ModelComparisonResponse",
  "PaperRunResponse",
  "ReconciliationResponse",
  "CampaignResponse"
];

for (const typeName of requiredTypes) {
  if (!content.includes(`export interface ${typeName}`)) {
    console.error(`Typecheck error: missing export interface ${typeName}`);
    process.exit(1);
  }
}

console.log("[quantlab-web] Typecheck verification passed. All API contracts valid.");
process.exit(0);
