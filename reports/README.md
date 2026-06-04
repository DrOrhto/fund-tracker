# Daily Fund Reports

This directory stores automatically generated Markdown reports.

GitHub Actions runs every day at 18:00 Beijing time and commits the generated report as `YYYY-MM-DD.md`.

The current implementation produces deterministic fallback metrics so the workflow can run before a real fund NAV data provider is connected.
