# mapir/desktop/resources

Placeholder for desktop UI assets that ship inside the package — for example
an application icon (.ico for Windows), splash bitmap, or bundled fonts.

Nothing is required here for the v0.3.0 build; PyInstaller picks up
`examples/`, `mapir/schemas/`, and `README.md` from the repo root, and the
dark theme is built from a palette dict in `mapir/desktop/theme.py`.

Add icons or other static resources here in a later release and reference
them from `mapir/desktop/app.py` via `mapir.utils.paths.resource_path`.
