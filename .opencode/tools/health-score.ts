import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "Calculate a project health score (0-100) based on OpenCode configuration validity, permission safety, agent coverage, tool utilization, and documentation completeness. Returns score with factor breakdown and improvement suggestions.",
  args: {
    configPath: tool.schema.string().describe("Path to opencode.json config file (default: auto-detect)").optional(),
    detailed: tool.schema.boolean().describe("Include detailed factor breakdown in output").optional(),
  },
  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "main.py")
    const venvPython = path.join(context.worktree, ".venv", "bin", "python3")

    const cmdArgs = [scriptPath, "--mode", "score"]
    if (args.configPath) cmdArgs.push("--config", args.configPath)
    if (args.detailed) cmdArgs.push("--verbose")

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
      return `Health score calculation failed: ${err.message}`
    }
  },
})
