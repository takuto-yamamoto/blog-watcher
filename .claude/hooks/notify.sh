#!/bin/bash

TITLE="${1:-Claude Code}"
MESSAGE="${2:-Waiting for your input}"
SOUND="${3:-Glass}"

notify_macos() {
    osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\" sound name \"$SOUND\""
}

notify_linux() {
    echo "Linux notification not yet implemented" >&2
    exit 1
}

notify_windows() {
    echo "Windows notification not yet implemented" >&2
    exit 1
}

case "$(uname -s)" in
Darwin)
    notify_macos
    ;;
Linux)
    notify_linux
    ;;
MINGW* | MSYS* | CYGWIN*)
    notify_windows
    ;;
*)
    echo "Unsupported OS: $(uname -s)" >&2
    exit 1
    ;;
esac
