const fs = require("fs");
const path = require("path");

function walk(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  list.forEach(file => {
    const full = path.join(dir, file);
    const stat = fs.statSync(full);
    if (stat && stat.isDirectory()) {
      if (file !== "node_modules" && !file.startsWith(".")) {
        results = results.concat(walk(full));
      }
    } else if (file.endsWith(".ts") || file.endsWith(".tsx")) {
      results.push(full);
    }
  });
  return results;
}

const root = path.resolve(__dirname, "..");
const files = walk(root);
let errors = 0;

for (const file of files) {
  const content = fs.readFileSync(file, "utf8");
  if (content.includes("debugger;")) {
    console.error(`Lint error in ${file}: debugger statement found`);
    errors++;
  }
}

if (errors > 0) {
  process.exit(1);
}

console.log(`[quantlab-web] Lint check passed for ${files.length} TypeScript source files.`);
process.exit(0);
