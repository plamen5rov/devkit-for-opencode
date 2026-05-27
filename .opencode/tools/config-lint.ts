import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Lint an OpenCode configuration file for schema violations, deprecated fields, and anti-patterns. Returns structured lint results with file paths, line numbers, severity levels, and fix suggestions.",
  args: {
    configPath: tool.schema.string().describe("Path to opencode.json config file (default: auto-detect)").optional(),
    fix: tool.schema.boolean().describe("Generate fixed config instead of just reporting issues").optional(),
  },
  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "main.py")
    const venvPython = path.join(context.worktree, ".venv", "bin", "python3")

    const cmdArgs = [scriptPath, "--mode", "audit"]
    if (args.configPath) cmdArgs.push("--config", args.configPath)
    if (args.fix) cmdArgs.push("--fix")

    try {
      let result
      try {
        result = await Bun.$`${venvPython} ${cmdArgs}`
      } catch {
        result = await Bun.$`python3 ${cmdArgs}`
      }

      return result.text().trim()
    } catch (error) {
      const err = error as Error
      return `Config lint failed: ${err.message}`
    }
  },
})
