# inkplate10-weather Example
Soldered Inkplate10 MicroPython NOAA Weather Example

### Setup dependancies
Micropython 1.18+ (using 1.20)
Driver files originally from:  https://github.com/SolderedElectronics/Inkplate-micropython.git
```
soldered_inkplate10.py
soldered_logo.py
gfx.py
gfx_standard_font_01.py
PCAL6416A.py
image.py
shapes.py
 ```
### Copy runtime deps to device using pyboard.py
```
python pyboard.py --device COM4 -f cp soldered_inkplate10.py soldered_logo.py gfx.py gfx_standard_font_01.py PCAL6416A.py image.py shapes.py :
```
### Copy this script to device using pyboard.py to special filename main.py 
See https://learn.adafruit.com/micropython-basics-load-files-and-run-code/boot-scripts) for additional context on MicroPython boot scripts
```
python pyboard.py --device COM4 -f cp NOAA_Weather.py :main.py
```
### Manually create btree db for storing SSID/Password
See https://docs.micropython.org/en/v1.10/library/btree.html
```
import btree
f = open("wifi_data", "w+b")
db = btree.open(f)
db[b"SSID"] = b"my-wifi-ssid"
db[b"password"] = b"my-wifi-password"
db.flush()
db.close()
f.close()
```
