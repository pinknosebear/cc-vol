## tt — cross-session coordination

you are working on a single task. your full context was injected at session start.

if you discover an unrelated bug or issue:
1. `tt add debug-<short-name> "<description>" --phase debug`
2. `tt log <your-task-id> --blocker "found <issue>, queued as debug-<short-name>"`
3. continue your own task. do NOT work on the debug task.

when done:
- `tt done <your-task-id>`

when blocked and cannot continue:
- `tt log <your-task-id> --blocker "what failed" --next "what to try"`
- stop. do not loop. another agent will pick this up.
