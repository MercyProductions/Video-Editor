const { rmSync, readdirSync, statSync } = require("node:fs");
const { join, relative } = require("node:path");
const { spawnSync } = require("node:child_process");

const root = join(__dirname, "..");
const outDir = join(root, ".test-dist");
const tsc = join(root, "node_modules", "typescript", "bin", "tsc");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: "inherit",
    shell: false,
    ...options
  });
  if (result.error) {
    console.error(result.error.message);
  }
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

function findTests(dir) {
  const rows = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) {
      rows.push(...findTests(path));
    } else if (entry.endsWith(".test.js")) {
      rows.push(path);
    }
  }
  return rows;
}

rmSync(outDir, { recursive: true, force: true });
run(process.execPath, [tsc, "-p", "tsconfig.test.json"]);

const tests = findTests(outDir);
if (!tests.length) {
  console.error("No compiled desktop unit tests found.");
  process.exit(1);
}

for (const test of tests) {
  console.log(`desktop unit: ${relative(outDir, test)}`);
  run(process.execPath, [test]);
}
