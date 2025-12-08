# THE GST DESK - Adjudication Software

## Overview
This is a complete desktop application for GST Department officers to manage adjudication proceedings, generate notices, and maintain taxpayer records.

## Features
- **Dashboard**: Quick access to all modules.
- **Taxpayers Database**: Import and search taxpayer details.
- **Adjudication Wizard**: Step-by-step process to generate notices (DRC-01, etc.).
- **Reports**: View and export generated cases.
- **Offline**: Works 100% offline without internet.

## Installation Instructions

### Step 1: Install Python
1. Download Python 3.11+ from [python.org](https://www.python.org/downloads/).
2. Run the installer and **CHECK THE BOX "Add Python to PATH"**.
3. Click "Install Now".

### Step 2: Setup the Software
1. Open the folder `GST_Adjudication_System`.
2. Open a terminal (Command Prompt) in this folder.
3. Run the following command to install required libraries:
   ```bash
   pip install -r requirements.txt
   ```

### Step 3: Run the Application
Double-click `main.py` or run in terminal:
```bash
python main.py
```

## How to Create .EXE (Executable)
To share this with other officers who don't have Python installed:
1. Double-click `build_exe.bat`.
2. Wait for the process to finish.
3. A new folder `dist` will be created. Inside, you will find `TheGSTDesk.exe`.
4. You can copy this `.exe` file anywhere and run it. Note: You might need to copy the `data` folder along with it if the data is not embedded correctly (the script attempts to embed it).

## Folder Structure
- `data/`: Contains `taxpayers.csv`, `cases.csv`, etc.
- `output/`: Generated PDF and Word documents are saved here.
- `src/`: Source code files.
- `main.py`: The starting point of the app.

## Troubleshooting
- If the app doesn't open, ensure you installed the requirements.
- If PDF generation fails, check if the `output` folder exists (it is created automatically).
"# gst" 
"# gst" 
# gst
