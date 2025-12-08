@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Building Executable...
pyinstaller --noconfirm --onefile --windowed --name "TheGSTDesk" --add-data "data;data" --add-data "src;src" main.py

echo Build Complete!
echo You can find the executable in the 'dist' folder.
pause
