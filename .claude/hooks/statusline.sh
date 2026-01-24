#!/bin/bash

input=$(cat)

model_display=$(echo "$input" | jq -r '.model.display_name')
current_dir=$(echo "$input" | jq -r '.workspace.current_dir')
context_size=$(echo "$input" | jq -r '.context_window.context_window_size')
context_usage=$(echo "$input" | jq '.context_window.current_usage')

git_branch=""
if git rev-parse &>/dev/null; then
    branch=$(git branch --show-current)
    if [ -n "$branch" ]; then
        git_branch="$branch"
    else
        commit_hash=$(git rev-parse --short HEAD 2>/dev/null)
        if [ -n "$commit_hash" ]; then
            git_branch="HEAD ($commit_hash)"
        fi
    fi
fi

current_tokens=$(echo "$context_usage" | jq '.input_tokens + .cache_creation_input_tokens + .cache_read_input_tokens')
percent_used=$((current_tokens * 100 / context_size))

# Create progress bar (20 characters wide)
bar_width=10
filled_count=$((percent_used * bar_width / 100))
empty_count=$((bar_width - filled_count))

# Build the progress bar
progress_bar="["
for ((i = 0; i < filled_count; i++)); do
    progress_bar+="="
done
for ((i = 0; i < empty_count; i++)); do
    progress_bar+="."
done
progress_bar+="]"

# ANSI color codes
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
MAGENTA='\033[35m'
CYAN='\033[36m'
RESET='\033[0m'

# Determine color based on percentage
if [ "$percent_used" -le 50 ]; then
    progress_color="$GREEN"
elif [ "$percent_used" -le 75 ]; then
    progress_color="$YELLOW"
else
    progress_color="$RED"
fi

model_display="${BLUE}${model_display}${RESET}"
current_dir="${CYAN}${current_dir##*/}${RESET}"
git_branch="${MAGENTA}${git_branch}${RESET}"
progress="${progress_color}${progress_bar} ${percent_used}%${RESET}"

# Output with color-coded progress bar
echo -e "$model_display :: ${current_dir##*/} :: $git_branch :: ${progress}"
