## Run

### Setup
```bash
sudo apt install ydotool evtest python3-evdev
```
Get mouse position of save button
```
python check_mouse_position.py
```
Save it in utils.py
```
MOUSE_POSITION = (0, 0)
```

### Download
Run download script. This will open windows one by one, move mouse to save them, watch for changes in download folder and parse files as they come.
```bash
python3 download.py \
  --stop -o thailand.csv --max_duration 2880 \
  -s Wrocław -s Warszawa -s Gdańsk -s Kraków -s Katowice -s Poznań \
  -e Bangkok \
  -d 01.02.2027-31.03.2027
```
Or if you know you want to spend specific weekend and number of days:
```bash
python3 download.py \
  --stop -o thailand.csv --max_duration 2880 \
  -s Wrocław -s Warszawa -s Gdańsk -s Kraków -s Katowice -s Poznań \
  -e Bangkok \
  --range-dates 5-10 --must-have-dates 01.03.2027-03.03.2027
```

### Filter results
```bash
python -m streamlit run filter.py
```
