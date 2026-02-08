# Troubleshooting Windows Rendering (GTK/Cairo/Pango)

The application uses **WeasyPrint** for live previews and PDF generation. WeasyPrint depends on several native libraries (GTK+, Cairo, Pango) that are not included with Python by default on Windows.

## Symptoms
- Preview window shows "Preview Unavailable".
- Application logs show `[STABILIZATION] Render worker failed`.
- Error messages mentioning `cairo`, `pango`, or `gobject` not found.

## Solution: Install GTK3 for Windows

Follow these steps to set up the necessary environment:

### 1. Download the GTK3 Installer
Download the latest GTK3 runtime installer for Windows from a reliable source like:
- [GTK for Windows (gvsbuild or similar)](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)

### 2. Add to Windows PATH
Ensure the GTK `bin` folder (e.g., `C:\Program Files\GTK3-Runtime-Win64\bin`) is added to your system's **Path** environment variable.

### 3. Verify Installation
Run the provided health check script to verify that the libraries are visible to Python:
```bash
python scripts/check_dependencies.py
```

## How Sandboxed Rendering Protects You
Even if your environment is missing these libraries, the application will **NOT** hang or crash. We use a "Sandboxed Rendering" architecture:
- Rendering logic is isolated in a separate background process.
- Each rendering task has a **5-second timeout**.
- If your environment is broken, the worker will fail safely without affecting the main GUI.

## Enabling Preview
Once you have installed the dependencies, you can enable the feature in `settings.json` or through the App Settings:
```json
{
    "render_enabled": true
}
```
