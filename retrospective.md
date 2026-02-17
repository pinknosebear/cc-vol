# Retrospective: Design-to-MVP in One Session

31 tasks, 200 tests, 3 phases, ~2 hours of wall clock. What worked, what was novel, and did `tt` actually matter?

---

## What we built

A volunteer scheduling system: FastAPI + SQLite + WhatsApp bot. Two-phase signup rules engine, coordinator tools, message parser, command dispatcher. The entire backend, tested, from a Google Sheet and a conversation.

## The workflow that emerged

1. **Decompose** requirements into atomic tasks with explicit file scopes and dependencies
2. **Parallelize** by launching agents into isolated git worktrees
3. **Orchestrate** from a single parent session that owns lifecycle (start, merge, done)
4. **Merge sequentially**, resolving conflicts as an integration step
5. **Test after every merge** — never let failures accumulate

---

## What had counterfactual impact (things that weren't free)

### 1. File-scope isolation prevented the default failure mode

The standard multi-agent failure is: two agents edit the same file, one wins, the other's work is lost or broken. This happened to us (p3-02 vs p3-03 both created `shifts.py`, p3-04 vs p3-05 both created `signups.py`, p3-07/08/09 all created `coordinator.py`).

The fix wasn't a tool feature — it was a design discipline: **before launching agents, analyze which files each task touches. If two tasks share a file, either make one depend on the other or split the file scope.** We learned this the hard way with the coordinator merge conflicts, then applied it proactively for the final batch (splitting `volunteer.py` into `vol_signup.py`, `vol_drop.py`, `vol_query.py`). That batch had zero conflicts.

Most agent workflows don't do this. They launch agents and hope for the best, or run everything sequentially. The file-scope analysis step is ~2 minutes of thinking that saves ~20 minutes of conflict resolution.

### 2. The orchestrator pattern (D12) was load-bearing

We tried having agents manage their own `tt start` / `tt done` / git worktrees. It failed repeatedly — permission issues, agents writing to wrong directories, lifecycle ordering bugs (merging after worktree deletion).

The pattern that worked: **the parent session owns all lifecycle operations. Agents are pure functions — they receive a worktree path, write code + tests, commit, and exit.** The parent handles: worktree creation, branch merging, conflict resolution, test verification, worktree cleanup.

This is not how most multi-agent setups work. Most either give agents full autonomy (which breaks on shared state) or run everything in one context (which limits parallelism). The orchestrator pattern gives you parallelism without shared-state bugs.

### 3. One-failure-mode task design made debugging trivial

Every task was scoped so it could only fail for one reason. `p2-03` (pure rules) couldn't fail because of DB issues — it has no DB. `p3-04` (create signup API) couldn't fail because of rule logic — it just calls the validator. When a test failed, you knew exactly where to look.

This is a design principle, not a tool feature. But `tt` enforced it by requiring explicit scope declarations in `plan.md`. You had to think about what files a task touches before it existed in the system.

### 4. The dependency graph enabled maximum parallelism

At peak, we had 9 agents running simultaneously (all Phase 3 API endpoints). This was only possible because the dependency graph told us exactly which tasks were unblocked. Without it, we'd have launched them sequentially or guessed wrong about ordering.

`tt next` made this mechanical — no thinking required about what can run in parallel.

## What tt did that existing tools also do

- **Task state tracking**: Any project board (Linear, Jira, even a markdown checklist) does this. `tt ls` is not novel.
- **Status reporting**: `tt report` is a convenience, not a capability.
- **Priority ordering**: Standard feature of every task tracker.

If `tt` were just a task list, it would have zero counterfactual impact. The value came from three specific features:

1. **`tt start` creates a git worktree** — this is the mechanical link between "task" and "isolated workspace." Without it, you need manual branch/worktree management for every agent launch.
2. **`tt plan` parses a structured plan file** with scopes and dependencies — this forces the decomposition discipline that makes parallel agents work.
3. **`tt next` computes the unblocked frontier** from the dependency graph — this makes parallelization decisions mechanical rather than manual.

## What we'd do differently

### Merge-before-done ordering

We lost a commit (p2-08) because `tt done` cleaned up the worktree before we merged. Lesson: always `git merge` → verify tests → `tt done`. This should probably be enforced by the tool.

### Test isolation as a template

Every API test file had the same `app.state.db` isolation bug. We fixed it 6 times. The test setup pattern (module-level `test_conn` + `_reset_db` reassigning `app.state.db`) should have been in a shared conftest.py or specified in the task prompt as a template.

### File scope in task spec, not just in our heads

The first two batches had implicit file scopes. When we made them explicit (the final batch), conflicts dropped to zero. File scope should be a required field in every task definition, and the orchestrator should refuse to launch two tasks with overlapping scopes in parallel.

## The actual insight

The hard part of multi-agent coding is not "running multiple agents." Any tool can spawn subprocesses. The hard part is **decomposition** — breaking work into pieces that are:

- **Isolated**: no shared mutable state (files, DB, config)
- **Testable**: each piece has its own verification
- **Composable**: pieces combine without integration surprises

`tt` helped because it formalized this decomposition into a structured artifact (`plan.md`) with machine-readable scopes and dependencies. But the real leverage was the thinking that went into that artifact — the design decisions (D1-D12), the file scope analysis, the dependency identification.

A coding agent without this decomposition discipline will produce code. A coding agent _with_ it will produce a system.
