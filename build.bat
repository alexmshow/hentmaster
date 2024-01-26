pip install pyinstaller
pip install -r requirements.txt
pyinstaller hent.py --icon=icon.ico --onefile --noconsole
mkdir dist\resources
copy resources dist\resources