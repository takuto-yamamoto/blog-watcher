---
description: Check current changes/branch, commit, and push
argument-hint: "[--no-branch]"
disable-model-invocation: true
allowed-tools: Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(git checkout:*), Bash(git switch:*)
---

## Arguments

$ARGUMENTS

- `--no-branch`: Push directly to main without creating a new branch

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`

## Your task

Based on the above changes:

1. If on main and `--no-branch` is NOT specified, create a new branch
2. Create a single commit with an appropriate message
3. Push the branch to origin

## Output

After completion, show:
- **Branch:** branch name
- **Commit:** commit hash and message
- **PR:** GitHub PR creation URL
