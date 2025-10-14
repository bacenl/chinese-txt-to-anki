@echo off
call .venv\Scripts\activate
python generate_anki_cards.py --no-api
pause
