import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Run DevKit analysis on an OpenCode configuration file. Analyzes permissions, agents, skills, MCP servers, and commands. Returns a comprehensive report with health score, security findings, and optimization recommendations.",
  args: {
    configPath: tool.schema.string().describe("Path to opencode.json config file (default: auto-detect)").optional(),
    mode: tool.schema.enum(["analyze", "audit", "score", "security", "token"]).describe("Analysis mode: analyze (full), audit (security), score (health), security (scan only), token (usage only)").optional(),
    verbose: tool.schema.boolean().describe("Enable verbose output").optional(),
  },
  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "main.py")
    const venvPython = path.join(context.worktree, ".venv", "bin", "python3")

    const cmdArgs = [scriptPath]
    if (args.configPath) cmdArgs.push("--config", args.configPath)
    if (args.mode) cmdArgs.push("--mode", args.mode)
    if (args.verbose) cmdArgs.push("--verbose")

    try {
      // Try venv python first, fallback to system python3
      let result
      try {
        result = await Bun.$`${venvPython} ${cmdArgs}`
      } catch {
        result = await Bun.$`python3 ${cmdArgs}`
      }

      return result.text().trim()
    } catch (error) {
      const err = error as Error
      return `DevKit analysis failed: ${err.message}`
    }
  },
})
