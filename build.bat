pip install pyinstaller -y
pyinstaller hent.py --icon=icon.ico --onefile --noconsole
mkdir dist\resources
copy resources dist\resources