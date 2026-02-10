# Execution Plan

Tasks to execute: 28
Retry limit: 3 per task
Max parallel: 5 per wave

## WAVE 1 (4 tasks)
1. [#1] Create skill error hierarchy
2. [#2] Create skill data models and enums
3. [#3] Create subagent error hierarchy
4. [#12] Create subagent data models

## WAVE 2 (5 tasks)
5. [#4] Implement SKILL.md loader and parser — after [#1, #2]
6. [#6] Implement skill registry — after [#1, #2]
7. [#8] Implement skill validation and trust levels — after [#2, #1]
8. [#13] Implement subagent config loader from markdown files — after [#3, #12]
9. [#22] Extend AgentConfig and AgentSettings with skill and subagent fields — after [#2, #12]

## WAVE 2b (1 task)
10. [#24] Extend UsageTracker for subagent token aggregation — after [#12]

## WAVE 3 (3 tasks)
11. [#7] Implement skill invocation and argument substitution — after [#2, #4]
12. [#5] Implement skill discovery from directories — after [#4, #6]
13. [#14] Implement subagent spawner — after [#12, #13, #3]

## WAVE 4 (2 tasks)
14. [#9] Implement SkillManager facade — after [#4, #5, #6, #7, #8]
15. [#15] Implement synchronous and asynchronous subagent delegation — after [#12, #14]

## WAVE 5 (5 tasks)
16. [#10] Create skills package __init__.py with public exports — after [#9]
17. [#11] Add unit tests for skills system (Phase 1) — after [#9]
18. [#23] Implement SkillTestHarness testing utility — after [#9]
19. [#20] Add skills parameters and methods to Agent facade — after [#9, #22]
20. [#16] Implement SubagentManager facade — after [#13, #14, #15]

## WAVE 6 (4 tasks)
21. [#17] Create subagents package __init__.py with public exports — after [#16]
22. [#18] Add unit tests for subagents system (Phase 2) — after [#16]
23. [#21] Add subagents parameters and methods to Agent facade — after [#16, #22, #24]
24. [#19] Implement Skills-Subagents bi-directional integration — after [#9, #16]

## WAVE 7 (4 tasks)
25. [#25] Update root __init__.py with new public API exports — after [#10, #17]
26. [#26] Add integration tests for skills-subagents workflows — after [#19, #20, #21]
27. [#27] Update CLAUDE.md with skills and subagents architecture — after [#20, #21]
28. [#28] Update CHANGELOG.md with skills and subagents features — after [#20, #21]
