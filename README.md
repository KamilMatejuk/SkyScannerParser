### Setup date ranges and cities
Get mouse position of save button
```
python check_mouse_position.py
```

Save it in utils.py
```
MOUSE_POSITION = (0, 0)
```

Run download script. This will open windows one by one, move mouse to save them, watch for changes in download folder and parse files as they come.
```bash
python download.py -s Kraków -s Wrocław -e Valetta -d 01.11.2025 -d 02.11.2025 --open 3
```

### Filter results
open `filter.ipynb`, set variables in first cell and run all
