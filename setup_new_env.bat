@echo off
echo Deleting existing venv if it exists...
if exist venv (
    rmdir /s /q venv
)

echo Creating new virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing requirements...
pip install -r requirements.txt

echo.
echo Virtual environment setup complete!
echo To activate it in the future, run: venv\Scripts\activate
pause
