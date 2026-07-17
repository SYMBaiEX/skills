export const meta = {
  name: "gpt-engineer-dynamic",
  description:
    "Research, plan, build, verify, and gap-close an engineering goal with bounded Claude subagent phases",
  whenToUse:
    "Use for repository-wide engineering goals that benefit from parallel discovery and verification plus a single coordinated writer.",
  phases: [
    { title: "Research", detail: "Map architecture, product behavior, and risk in parallel", model: "sonnet" },
    { title: "Plan", detail: "Turn evidence into an ordered implementation contract", model: "opus" },
    { title: "Build", detail: "Implement the approved plan with one coordinated writer", model: "sonnet" },
    { title: "Verify", detail: "Cross-check behavior, tests, and residual gaps", model: "sonnet" },
    { title: "Close", detail: "Repair confirmed gaps in bounded cycles and report evidence", model: "opus" },
  ],
}

let input = args ?? {}
if (typeof input === "string") {
  try {
    input = JSON.parse(input)
  } catch {
    input = { goal: input }
  }
}
const goal = String(input.goal ?? "").trim()
if (!goal) {
  return {
    status: "blocked",
    complete: false,
    cycles: 0,
    gaps: ["Pass a non-empty goal through args.goal or as command input."],
    evidence: [],
  }
}

const scope = String(input.scope ?? "the current repository")
const acceptance = Array.isArray(input.acceptance) ? input.acceptance.map(String) : []
const requestedCycles = Number.isInteger(input.maxCycles) ? input.maxCycles : 2
const maxCycles = Math.max(1, Math.min(requestedCycles, 3))
const contract = `
Goal: ${goal}
Scope: ${scope}
Acceptance criteria: ${acceptance.length ? acceptance.join("; ") : "Infer concrete criteria from the goal and repository instructions."}

Read every applicable AGENTS.md and CLAUDE.md. Preserve all pre-existing user changes. Do not commit,
push, deploy, message external systems, or use production credentials unless the goal explicitly grants
that authority. Back every completion claim with paths, commands, or runtime evidence.
`

const FINDINGS_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    area: { type: "string" },
    findings: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: { type: "string" },
          evidence: { type: "string" },
          impact: { type: "string" },
          recommendation: { type: "string" },
        },
        required: ["id", "evidence", "impact", "recommendation"],
      },
    },
    risks: { type: "array", items: { type: "string" } },
  },
  required: ["area", "findings", "risks"],
}

const PLAN_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    tasks: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: { type: "string" },
          paths: { type: "array", items: { type: "string" } },
          objective: { type: "string" },
          dependsOn: { type: "array", items: { type: "string" } },
          checks: { type: "array", items: { type: "string" } },
        },
        required: ["id", "paths", "objective", "dependsOn", "checks"],
      },
    },
    integrationChecks: { type: "array", items: { type: "string" } },
    prohibitedEffects: { type: "array", items: { type: "string" } },
  },
  required: ["tasks", "integrationChecks", "prohibitedEffects"],
}

const VERIFY_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    area: { type: "string" },
    passed: { type: "boolean" },
    commands: { type: "array", items: { type: "string" } },
    evidence: { type: "array", items: { type: "string" } },
    gaps: { type: "array", items: { type: "string" } },
  },
  required: ["area", "passed", "commands", "evidence", "gaps"],
}

phase("Research")
const research = (area, prompt) => agent(
  `${contract}\nYou are the read-only ${area} explorer. ${prompt} Do not edit. Return only evidenced findings.`,
  { label: `research:${area}`, phase: "Research", model: "sonnet", effort: "high", schema: FINDINGS_SCHEMA },
)
const discoveries = (await parallel([
  () => research("architecture", "Trace execution paths, boundaries, SDK usage, dependencies, and shared contracts."),
  () => research("product", "Walk user-visible journeys, failure states, incomplete behavior, TODOs, stubs, mocks, and dead paths."),
  () => research("quality", "Inspect tests, CI, security-sensitive surfaces, deprecated code, operational risks, and verification gaps."),
])).filter(Boolean)
if (discoveries.length !== 3) {
  return {
    status: "failed",
    complete: false,
    cycles: 0,
    gaps: ["One or more required research shards did not return a valid result."],
    evidence: [],
  }
}

phase("Plan")
const plan = await agent(
  `${contract}\nResearch evidence:\n${JSON.stringify(discoveries)}\n\nAct as the lead engineer. Reconcile contradictions, reject unsupported findings, and produce a dependency-ordered plan. Give one coordinated writer exact path ownership and concrete checks. Do not edit.`,
  { label: "plan", phase: "Plan", model: "opus", effort: "high", schema: PLAN_SCHEMA },
)
if (!plan || !plan.tasks.length) {
  return {
    status: "blocked",
    complete: false,
    cycles: 0,
    gaps: ["Planning produced no executable tasks."],
    evidence: discoveries.flatMap(result => result.findings.map(finding => finding.evidence)),
  }
}

phase("Build")
const build = await agent(
  `${contract}\nImplementation plan:\n${JSON.stringify(plan)}\n\nYou are the sole writer. Implement every supported task in dependency order, preserve unrelated work, inspect each diff, and run focused checks. Do not commit, push, deploy, or leave placeholders. Return changed files, commands, failures, and residual risks.`,
  { label: "build", phase: "Build", model: "sonnet", effort: "high" },
)
if (!build) {
  return {
    status: "failed",
    complete: false,
    cycles: 0,
    gaps: ["The required build writer did not return a valid result."],
    evidence: [],
  }
}

let cycle = 0
let verification = []
let closure = null
const repairs = []
while (cycle < maxCycles) {
  const cycleNumber = cycle + 1
  phase("Verify")
  const verify = (area, prompt) => agent(
    `${contract}\nPlan:\n${JSON.stringify(plan)}\nBuild report:\n${JSON.stringify(build)}\nRepair reports:\n${JSON.stringify(repairs)}\n\nYou are the read-only ${area} verifier. ${prompt} Inspect the integrated repository state; do not edit. A natural-language claim is not evidence.`,
    { label: `verify:${area}:${cycleNumber}`, phase: "Verify", model: "sonnet", effort: "high", schema: VERIFY_SCHEMA },
  )
  verification = (await parallel([
    () => verify("correctness", "Review the diff and execution paths for correctness, regressions, scope violations, and missing requirements."),
    () => verify("tests", "Run or inspect the most relevant static checks, tests, and build commands. Record exact commands and failures."),
    () => verify("completion", "Search for residual TODOs, stubs, mocks, incomplete user journeys, deprecated paths, and unsupported completion claims."),
  ])).filter(Boolean)
  cycle = cycleNumber

  if (verification.length !== 3) {
    closure = {
      complete: false,
      gaps: ["One or more required verification shards did not return a valid result."],
      evidence: [],
      status: "failed",
    }
    break
  }
  const verifierGaps = verification.flatMap(result => result.gaps ?? [])
  const allVerifiersPassed = verification.every(
    result => result.passed === true && (result.gaps?.length ?? 0) === 0,
  )

  phase("Close")
  closure = await agent(
    `${contract}\nPlan:\n${JSON.stringify(plan)}\nVerification cycle ${cycle}:\n${JSON.stringify(verification)}\n\nDecide whether the goal is evidence-backed complete. Return JSON with keys complete (boolean), gaps (string array), evidence (string array), and status (complete, partial, blocked, or failed). Do not edit.`,
    {
      label: `close:${cycle}`,
      phase: "Close",
      model: "opus",
      effort: "high",
      schema: {
        type: "object",
        additionalProperties: false,
        properties: {
          complete: { type: "boolean" },
          gaps: { type: "array", items: { type: "string" } },
          evidence: { type: "array", items: { type: "string" } },
          status: { enum: ["complete", "partial", "blocked", "failed"] },
        },
        required: ["complete", "gaps", "evidence", "status"],
      },
    },
  )
  if (!closure) break
  if (!allVerifiersPassed) {
    closure = {
      complete: false,
      gaps: [...new Set([...verifierGaps, ...closure.gaps])],
      evidence: closure.evidence,
      status: ["blocked", "failed"].includes(closure.status) ? closure.status : "partial",
    }
  }
  if (closure.complete && (closure.status !== "complete" || closure.gaps.length > 0)) {
    closure = {
      complete: false,
      gaps: [...new Set(["Closure result was internally inconsistent.", ...closure.gaps])],
      evidence: closure.evidence,
      status: "failed",
    }
  }
  if (closure.complete) break
  if (["blocked", "failed"].includes(closure.status)) break
  if (!closure.gaps.length) {
    closure = {
      complete: false,
      gaps: ["Completion was not proven, but no actionable gap was returned."],
      evidence: closure.evidence,
      status: "blocked",
    }
    break
  }

  if (cycle >= maxCycles) break
  phase("Build")
  const repair = await agent(
    `${contract}\nConfirmed gaps after verification:\n${JSON.stringify(closure.gaps)}\n\nYou are the sole repair writer. Fix every confirmed in-scope gap, preserve unrelated work, and rerun focused checks. Do not commit, push, or deploy.`,
    { label: `repair:${cycle}`, phase: "Build", model: "sonnet", effort: "high" },
  )
  if (!repair) {
    closure = {
      complete: false,
      gaps: ["The required repair writer did not return a valid result.", ...closure.gaps],
      evidence: closure.evidence,
      status: "failed",
    }
    break
  }
  repairs.push(repair)
}

return {
  status: closure?.status ?? "failed",
  complete: closure?.complete ?? false,
  cycles: cycle,
  plan,
  build,
  repairs,
  verification,
  gaps: closure?.gaps ?? ["Workflow ended without a valid closure decision."],
  evidence: closure?.evidence ?? [],
}
