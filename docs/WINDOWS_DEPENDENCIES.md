# Windows Runtime Dependencies

This application uses **WeasyPrint** for high-fidelity PDF generation and preview rendering. WeasyPrint relies on the **GTK3** runtime libraries (specifically Pango, GDK-Pixbuf, and Cairo), which are not included with standard Python installations on Windows.

## Error Symptoms
If these dependencies are missing, you will see:
*   **Preview Skipped** or **Generation Failed** in the application.
*   Logs showing `OSError: [WinError 126] The specified module could not be found` or `0x7e`.
*   Logs mentioning `cannot load library 'gobject-2.0-0'` or `pango`.

## Installation Instructions

To resolve this, you must install the GTK3 runtime for Windows.

### Option 1: Standalone Installer (Recommended)
1.  Download the **GTK3 runtime installer** from the official WeasyPrint documentation or trusted sources (e.g., github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer).
    *   *Note: Ensure you download the version matching your Python architecture (usually 64-bit).*
2.  Run the installer.
3.  **Crucial Step**: During installation, ensure the option **"Set up PATH environment variable"** is checked. This allows the application to find the libraries.
4.  Restart the computer (or fully restart the application) to ensure the new PATH is picked up.

### Option 2: MSYS2 (Advanced)
If you use MSYS2:
1.  Open MSYS2 terminal.
2.  Run: `pacman -S mingw-w64-x86_64-gtk3`
3.  Add the MSYS2 `mingw64/bin` directory to your System PATH.

## Verification
After installation, the "Preview" feature in the application should function correctly without errors.
