---
name: pr
description: Manage PRs (create/list/view)
argument-hint: [create|list|view [--comments]]
allowed-tools: Bash(gh pr create:*), Bash(gh pr list:*), Bash(gh pr view:*), Bash(git log:*), Bash(git diff:*)
---

## Context
- Branch: !`git branch --show-current`
- Command: $ARGUMENTS

## Task

Based on $ARGUMENTS, execute:

- **create**:
  1. Analyze `git log main..HEAD` and `git diff main...HEAD --stat`
  2. Run `gh pr create --base main` with summary/test plan body
- **list**: Run `gh pr list` and display results
- **view**: Run `gh pr view` for current branch's PR
- **view --comments**:
  1. Run `gh pr view --comments`
  2. Analyze the feedback and share your opinion on how to address each comment
  3. Start discussion
- **empty/unknown**: Show available subcommands (create, list, view)
