git stash
git pull
source .venv/bin/activate
python -m pip install -r requirements.txt
playwright install
playwright install-deps

