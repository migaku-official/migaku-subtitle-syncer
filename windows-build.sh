#!/bin/sh

rm -rf .venv build dist &&
        vagrant up windows &&
        vagrant winrm windows --command "cd c:\vagrant ; poetry config virtualenvs.in-project true ; poetry install ; poetry run pyinstaller --onefile --clean --add-binary 'binaries/windows;.' migaku-subtitle-syncer.py"
