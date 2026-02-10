# Execution Plan

Tasks to execute: 13
Retry limit: 3 per task
Max parallel: 5 per wave

## WAVE 1 (3 tasks)
1. [#18] Remove bidirectional dependency between SkillManager and SubagentManager
2. [#17] Add record_subagent_usage() public method to UsageTracker
3. [#19] Add ReAct tool state save/restore around workflow run

## WAVE 2 (3 tasks)
4. [#20] Replace lazy property initialization with explicit init_skills() and init_subagents() — after [#18]
5. [#22] Redesign activate_with_fork() as fully async — after [#18]
6. [#27] Update ReAct workflow tests for tool cleanup behavior — after [#19]

## WAVE 3 (2 tasks)
7. [#21] Update Agent facade to wire managers through integration module — after [#18, #20]
8. [#23] Make Agent.invoke_skill() async and add invoke_skill_sync() wrapper — after [#22]

## WAVE 4 (2 tasks)
9. [#24] Register invoke_skill pydantic-ai tool when skills are initialized — after [#20, #22, #23]
10. [#26] Update existing skill and subagent tests for new API signatures — after [#17, #18, #20, #22, #23]

## WAVE 5 (2 tasks)
11. [#25] Update invoke_skill tool description dynamically when skills change — after [#24]
12. [#28] Write 6 regression tests for resolved fragility points — after [#17, #18, #19, #20, #22, #24]

## WAVE 6 (1 task)
13. [#29] Verify coverage targets and update CLAUDE.md fragility points — after [#26, #27, #28]
