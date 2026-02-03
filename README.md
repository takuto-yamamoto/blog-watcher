# blog-watcher

A simplified, blog-focused monitoring tool.

This project provides a streamlined experience specifically designed for monitoring blog sites, making it easier to track updates from your favorite blogs without the complexity of a general-purpose change detection system.

## Features

- **Blog-focused simplicity**: Streamlined interface optimized for blog monitoring
- **Multiple blog tracking**: Monitor multiple blog URLs simultaneously
- **Automatic change detection**: Detect new posts and content updates
- **Notifications**: Receive alerts when your favorite blogs are updated
- **Easy configuration**: Simple setup compared to general-purpose monitoring tools

## Build

### Build with Python

```bash
# Install the build helper
python -m pip install build

# Build a wheel
python -m build --wheel
```

### Build with Hatch

```bash
hatch build
```

## Installation

You can install with standard `pip install`.

```bash
python -m pip install dist/blog_watcher-0.1.0-py3-none-any.whl
```

Alternatively, you can install cleanly with pipx.

```bash
pipx install dist/blog_watcher-0.1.0-py3-none-any.whl
```

## Usage

```bash
# Show CLI help
blog-watcher --help

# Run continuously
blog-watcher -c path/to/config.toml

# Run once with a config file and custom DB path
blog-watcher -c path/to/config.toml --once --db-path blog_states.sqlite
```

Behavior:
- On the first run, a single "Initial sync completed" notification is sent per blog.
- Subsequent runs only notify when a blog changes.

## Config

```toml
[slack]
webhook_url = "$SLACK_WEBHOOK_URL"

[[blogs]]
name = "Example Blog"
url = "https://example.com"

[[blogs]]
name = "Another Blog"
url = "https://example.org"
```

Notes:
- `slack` is required and only `webhook_url` is accepted.
- `blogs` must be a non-empty list; each entry requires `name` and `url`.
- Unknown keys are rejected.

## Author

takuto-yamamoto

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
