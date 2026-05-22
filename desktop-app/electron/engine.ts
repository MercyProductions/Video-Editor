import { spawn } from "node:child_process";

export type EngineResult = {
  ok: boolean;
  stdout: string;
  stderr: string;
  exitCode: number | null;
};

export async function runEngineCommand(options: {
  pythonBinary: string;
  renderPy: string;
  engineRoot: string;
  args: string[];
}): Promise<EngineResult> {
  return new Promise((resolve) => {
    const child = spawn(options.pythonBinary, [options.renderPy, ...options.args], {
      cwd: options.engineRoot,
      windowsHide: true
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    child.on("close", (exitCode) => {
      resolve({ ok: exitCode === 0, stdout, stderr, exitCode });
    });
  });
}
