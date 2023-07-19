# inkplate10-weather Example
Soldered Inkplate10 MicroPython NOAA Weather Example

### Flash Micropython onto board
* Determine serial port used (dmesg on linux/Device Manager on Windows), replace COM4 with appropriate device
    *  e.g. `/dev/ttyUSB0` or `COM1`, etc.
* See https://github.com/espressif/esptool for details on esptool.py utility (requires pyserial)
* See https://micropython.org/download/esp32spiram/ for details and download micropython release builds available for the `esp32spiram` variant (compatible with Soldered Inkplate 10)
    * `https://micropython.org/resources/firmware/esp32spiram-20230426-v1.20.0.bin` is build used here
* Download / Install Python bits
```
curl -O https://github.com/micropython/micropython/raw/master/tools/pyboard.py
curl -O https://micropython.org/resources/firmware/esp32spiram-20230426-v1.20.0.bin
pip install pyserial
```
* Erase Flash from factory image and write the latest Micropython build
```
esptool.py --chip esp32 --port COM4 erase_flash
python esptool.py --chip esp32 --port COM4 write_flash -z 0x1000 esp32spiram-20230426-v1.20.0.bin
```

### Setup dependancies from specific board (Soldered Inkplate 10)
Micropython 1.18+ (using 1.20)
Driver files originally from:  https://github.com/SolderedElectronics/Inkplate-micropython.git and also included for simplicity in this repository.
* Clone this repo:
```
git clone https://github.com/daemonhorn/inkplate10-weather.git
cd inkplate10-weather
```
* Base dependancy file list:
`soldered_inkplate10.py
soldered_logo.py
gfx.py
gfx_standard_font_01.py
PCAL6416A.py
image.py
shapes.py`

### Copy runtime deps to device using pyboard.py
See https://docs.micropython.org/en/latest/reference/pyboard.py.html
```
python pyboard.py --device COM4 -f cp soldered_inkplate10.py soldered_logo.py gfx.py gfx_standard_font_01.py PCAL6416A.py image.py shapes.py :
```
### Copy this script to device using pyboard.py to special filename main.py 
See https://learn.adafruit.com/micropython-basics-load-files-and-run-code/boot-scripts) for additional context on MicroPython boot scripts
```
python pyboard.py --device COM4 -f cp NOAA_Weather.py :main.py
```
### Manually create btree db for storing SSID/Password from repl `>>>` prompt
See https://docs.micropython.org/en/v1.10/library/btree.html
1. Boot the device
2. Attach favorite serial terminal application to correct port (see below for example)
3. Hit control-c to abort any running script (before sleep)
4. Wait for Micropython repl prompt `>>>`
5. Hit control+E to go into copy/paste compatible mode
6. Paste text below (adjust ssid/psw values to those for your network)
7. Hit control+D to execute pasted code
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
### Debug using your favorite serial terminal (putty/cu, etc.)
* Setup terminal for appropriate serial port (COM4), bitrate (115200), Data/Stop/Parity (8/N/1)
* Save it to a profile/settings file to make it sticky
1. Start Terminal with profile
```
putty --load "Inkplate10-COM4"
```
2. Power/Boot device (reset button on back or power button next to usb-c connector as applicable)
3. Example serial debug output on `power-on` when wifi connects, syncs with ntp, fetches data, and displays on e-ink
```
rst:0x1 (POWERON_RESET),boot:0x12 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
mode:DIO, clock div:2
load:0x3fff0030,len:4656
load:0x40078000,len:13284
ho 0 tail 12 room 4
load:0x40080400,len:3712
entry 0x4008064c
connecting to network...
network config: ('10.0.20.72', '255.255.255.0', '10.0.20.1', '8.8.8.8')
Debug: Fetching time from ntp server
Current Time: (2023, 7, 19, 2, 11, 59, 30, 153)
Debug: Finished fetching data
Debug: Finished reading temperature sensor.
Debug: Starting final render on display.
Mono: clean 1690ms (33ms ea), draw 594ms (99ms ea), total 2284ms
Debug: Going to Sleep
```
3. Example from `deepsleep`:
```
rst:0x5 (DEEPSLEEP_RESET),boot:0x12 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
mode:DIO, clock div:2
load:0x3fff0030,len:4656
load:0x40078000,len:13284
ho 0 tail 12 room 4
load:0x40080400,len:3712
entry 0x4008064c
woke from a deep sleep
connecting to network...
network config: ('10.0.20.72', '255.255.255.0', '10.0.20.1', '8.8.8.8')
Current Time: (2023, 7, 19, 2, 13, 42, 48, 876779)
Debug: Finished fetching data
Debug: Finished reading temperature sensor.
Debug: Starting final render on display.
Partial: draw 599ms (119ms/frame 145us/row) (y=0..825)
Debug: Going to Sleep
```
