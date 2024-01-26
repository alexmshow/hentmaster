pip install pyinstaller
pip install -r requirements.txt
pyinstaller hent.py --icon=icon.ico --onefile --noconsole -n HentaiMaster
mkdir dist\resources
copy resources dist\resources