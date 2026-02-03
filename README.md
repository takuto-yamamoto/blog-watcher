# blog-watcher

A simplified, blog-focused monitoring tool.

This project provides a streamlined experience specifically designed for monitoring blog sites, making it easier to track updates from your favorite blogs without the complexity of a general-purpose change detection system.

## Features

- **Blog-focused simplicity**: Streamlined interface optimized for blog monitoring
- **Multiple blog tracking**: Monitor multiple blog URLs simultaneously
- **Automatic change detection**: Detect new posts and content updates
- **Notifications**: Receive alerts when your favorite blogs are updated
- **Easy configuration**: Simple setup compared to general-purpose monitoring tools

## Installation

```bash
# Build a wheel (PEP 517)
python -m build --wheel

# Install from the built wheel
python -m pip install dist/blog_watcher-0.1.0-py3-none-any.whl

# Or install via pipx (isolated, recommended for CLI)
pipx install dist/blog_watcher-0.1.0-py3-none-any.whl
```

## Usage

```bash
# Show CLI help
blog-watcher --help

# Run once with a config file and custom DB path
blog-watcher -c path/to/config.toml --once --db-path blog_states.sqlite
```

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
