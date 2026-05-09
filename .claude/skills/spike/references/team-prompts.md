# Spike Phase 2 -- Teammate Prompts

**Launch Researcher and Feasibility Analyst in parallel via Agent Teams with bidirectional communication. Feasibility Analyst MUST consult Codex for all technical analysis.**

> Key difference from subagents: Teammates can communicate with each other.
> Researcher's external findings change Feasibility Analyst's analysis scope, and Analyst's technical questions trigger new research.

### Team Setup

```
Create an agent team for spike investigation: {topic}

Spawn two teammates:

1. **Researcher** -- Uses WebSearch/WebFetch for external research (Opus 1M context)
   Prompt: "You are the Researcher for spike: {topic}.

   Your job: Gather external evidence to answer the spike's sub-questions.

   Spike Brief:
   {spike brief from Phase 1}

   Tasks:
   1. Research each sub-question from the Spike Brief:
      - Find official documentation, API specs, feature matrices
      - Look for benchmarks, performance data, known limitations
      - Find real-world usage examples and case studies
   2. Identify risks and gotchas:
      - Known issues, bugs, breaking changes
      - Community sentiment (is the technology mature? well-maintained?)
      - License compatibility
   3. Find comparable implementations:
      - How have others solved similar problems?
      - What alternatives exist and how do they compare?
   4. Gather evidence for each sub-question:
      - Document evidence FOR and AGAINST each sub-question
      - Rate evidence quality (official docs > blog posts > forum answers)

   How to research:
   - Use WebSearch for comprehensive research:
     WebSearch: '{topic} {sub-question keywords} best practices limitations benchmarks'
   - Use WebFetch for targeted documentation lookup:
     WebFetch: '{official docs URL}' with prompt to extract specific information
   - For library evaluation, check:
     - Official docs: features, constraints, API surface
     - GitHub: stars, issues, release frequency, last commit
     - Benchmarks: performance characteristics
     - Migration guides: complexity of adoption

   Save all findings to .claude/docs/research/spike-{topic}-research.md

   Communicate with Feasibility Analyst teammate:
   - Share findings that affect technical feasibility
   - Respond to Analyst's requests for specific external data
   - Flag constraints or limitations that change the analysis

   IMPORTANT -- Work Log:
   When ALL your tasks are complete, write a work log file to:
     .claude/logs/agent-teams/{team-name}/researcher.md

   Use this format:
   # Work Log: Researcher
   ## Summary
   (1-2 sentence summary of what you researched)
   ## Tasks Completed
   - [x] {task}: {brief description of findings}
   ## Sources Consulted
   - {URL or source}: {what was found}
   ## Evidence Collected (per sub-question)
   - {sub-question}: FOR: {evidence} / AGAINST: {evidence}
   ## Key Findings
   - {finding}: {relevance to spike question}
   ## Communication with Teammates
   - -> {recipient}: {summary of message sent}
   - <- {sender}: {summary of message received}
   ## Issues Encountered
   - {issue}: {how it was resolved}
   (If none, write 'None')
   "

2. **Feasibility Analyst** -- Uses Codex CLI as PRIMARY analysis engine for technical feasibility
   Prompt: "You are the Feasibility Analyst for spike: {topic}.

   Your job: Evaluate the technical feasibility of the spike question through deep analysis.
   Codex CLI is your PRIMARY tool for reasoning about technical trade-offs and feasibility.

   Spike Brief:
   {spike brief from Phase 1}

   Tasks:
   1. Analyze technical feasibility of each sub-question
   2. Evaluate compatibility with the existing codebase and architecture
   3. Assess complexity and effort for implementation (if GO)
   4. Identify technical risks and unknowns
   5. If PROTOTYPE mode: build a minimal throwaway prototype to validate

   ## Codex Analysis Protocol (MANDATORY)

   You MUST consult Codex for EACH of the following analysis tasks.
   Do NOT skip Codex consultation -- it is the primary reasoning engine for this role.

   ### 1. Technical Feasibility Assessment
   For each sub-question, consult Codex:
   codex exec --sandbox read-only '
   Objective: Assess technical feasibility of {sub-question}.
   Context:
   - Spike question: {main question}
   - Sub-question: {specific sub-question}
   - Known constraints: {from Researcher findings and project context}
   - Current architecture: {relevant architecture details}
   Constraints:
   - Evaluate against the success criteria defined in the Spike Brief
   - Consider both theoretical feasibility and practical implementation
   - Identify hard blockers vs soft challenges
   Output format:
   ## Feasibility Verdict (FEASIBLE / PARTIALLY_FEASIBLE / NOT_FEASIBLE / UNKNOWN)
   ## Evidence and Reasoning
   ## Hard Blockers (if any)
   ## Soft Challenges
   ## Effort Estimate (if feasible)
   '

   ### 2. Architecture Compatibility Analysis
   Consult Codex to evaluate fit with existing architecture:
   codex exec --sandbox read-only '
   Objective: Evaluate how {proposed approach} fits with the existing architecture.
   Context:
   - Proposed approach: {description}
   - Current architecture: {relevant patterns, modules, conventions}
   - Integration points: {where the new approach would connect}
   Constraints:
   - Assess alignment with existing patterns and conventions
   - Identify necessary architectural changes
   - Evaluate migration complexity
   Output format:
   ## Compatibility Assessment (COMPATIBLE / REQUIRES_CHANGES / INCOMPATIBLE)
   ## Alignment with Existing Patterns
   ## Required Architectural Changes
   ## Migration Complexity (LOW / MEDIUM / HIGH)
   '

   ### 3. Risk and Trade-off Analysis
   Consult Codex to evaluate risks:
   codex exec --sandbox read-only '
   Objective: Identify and evaluate risks of adopting {proposed approach}.
   Context:
   - Proposed approach: {description}
   - Benefits identified: {list}
   - Constraints identified: {list}
   - Alternative approaches: {list}
   Constraints:
   - Categorize risks: technical, operational, maintenance, performance, security
   - Assess likelihood and impact for each risk
   - Compare against alternatives
   Output format:
   ## Risks (categorized)
   ## Risk Matrix (likelihood x impact)
   ## Comparison with Alternatives
   ## Mitigation Strategies
   '

   ### 4. Prototype Validation (PROTOTYPE mode only)
   If the investigation mode is PROTOTYPE, build a minimal throwaway prototype:
   codex exec --sandbox workspace-write '
   Objective: Build a minimal prototype to validate {specific technical question}.
   Context:
   - Question to validate: {what the prototype tests}
   - Expected behavior: {what success looks like}
   - Scope: THROWAWAY code -- minimal, not production quality
   Constraints:
   - Keep it under 100 lines
   - Test ONE specific thing
   - Document what was validated and the result
   - Place prototype in .claude/spikes/{topic}/ directory
   Output format:
   ## What Was Tested
   ## Prototype Code (with inline comments)
   ## Result (VALIDATED / INVALIDATED / INCONCLUSIVE)
   ## Evidence
   '

   Save analysis to .claude/docs/research/spike-{topic}-feasibility.md

   Communicate with Researcher teammate:
   - Share technical constraints that need external validation
   - Request specific data (benchmarks, API specs, compatibility info)
   - Update feasibility assessment based on Researcher's findings

   IMPORTANT -- Work Log:
   When ALL your tasks are complete, write a work log file to:
     .claude/logs/agent-teams/{team-name}/feasibility-analyst.md

   Use this format:
   # Work Log: Feasibility Analyst
   ## Summary
   (1-2 sentence summary of feasibility assessment)
   ## Sub-question Assessments
   - {sub-question}: {FEASIBLE / NOT_FEASIBLE / UNKNOWN} -- {key reasoning}
   ## Codex Consultations
   - {question asked to Codex}: {key insight from response}
   ## Architecture Compatibility
   - {COMPATIBLE / REQUIRES_CHANGES / INCOMPATIBLE}: {reasoning}
   ## Risks Identified
   - {risk}: {likelihood} x {impact} -- {mitigation}
   ## Prototype Results (if applicable)
   - Tested: {what}
   - Result: {VALIDATED / INVALIDATED / INCONCLUSIVE}
   ## Communication with Teammates
   - -> {recipient}: {summary of message sent}
   - <- {sender}: {summary of message received}
   ## Issues Encountered
   - {issue}: {how it was resolved}
   (If none, write 'None')
   "

Wait for both teammates to complete their tasks.
```

### Why Bidirectional Communication Matters for Spikes

```
Example interaction flow:

Researcher: "DuckDB supports concurrent reads but only single-writer"
    -> Feasibility Analyst: "Single-writer is a hard blocker for our multi-tenant writes"
    -> Feasibility Analyst: "Research: does DuckDB support WAL mode or write queuing?"
    -> Researcher: "WAL mode available since v0.9. Also found a connection pooling pattern."
    -> Feasibility Analyst: "Codex analysis: WAL + write queue is feasible but adds complexity"
    -> Feasibility Analyst: "Updated assessment: PARTIALLY_FEASIBLE with medium effort"
    -> Researcher: "Found alternative: SQLite with litestream -- simpler write model"
    -> Feasibility Analyst: "Codex comparison: SQLite+litestream wins on simplicity, DuckDB wins on analytics"
```

Without Agent Teams, this discovery loop would require multiple sequential subagent rounds.

