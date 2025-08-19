@echo off
set PATH=C:\Program Files\Tesseract-OCR;%PATH%
echo Tesseract added to PATH for this session
echo Run: tesseract --version to test
echo Run: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
