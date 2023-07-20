# This script is generally saved as main.py on esp32 spiflash filesystem
# Setup dependancies
#
# Micropython 1.18+ (using 1.20)
# Driver files:  https://github.com/SolderedElectronics/Inkplate-micropython.git
#   soldered_inkplate10.py
#   soldered_logo.py
#   gfx.py
#   gfx_standard_font_01.py
#   PCAL6416A.py
#   image.py
#   shapes.py
# 
# Copy runtime deps to device using pyboard.py
# python pyboard.py --device COM4 -f cp soldered_inkplate10.py soldered_logo.py gfx.py gfx_standard_font_01.py PCAL6416A.py image.py shapes.py :

# Copy this script to device using pyboard.py to special filename main.py (See https://learn.adafruit.com/micropython-basics-load-files-and-run-code/boot-scripts) for additional context on MicroPython boot scripts
# python pyboard.py --device COM4 -f cp NOAA_Weather.py :main.py
#
# Manually create btree db for storing SSID/Password
# import btree
# f = open("wifi_data", "w+b")
# db = btree.open(f)
# db[b"SSID"] = b"my-wifi-ssid"
# db[b"password"] = b"my-wifi-password"
# db.flush()
# db.close()
# f.close()






#import network
#import time
#from soldered_inkplate10 import Inkplate


# Function to init Realtime Clock, and sync with NTP server
def setup_rtc():
    from machine import RTC
    import ntptime
    import time
    rtc = RTC()
  
    utcTime = rtc.datetime()    # get the date and time in UTC
    localtimeOffset = -4
    #print("Debug times: %s,%s" % (str(localTime),str(curTime)))

    ntptime.host = '1.north-america.pool.ntp.org'
    ntptime.timeout = 5
    
    #If the year is 2000, rtc is not initialized, use ntp
    if utcTime[0] == 2000:
        print("Debug: Fetching time from ntp server")
        try: 
            ntptime.settime() # set the rtc datetime from the remote server
        except:
            print("Transient error setting the time from ntp, retrying with timeout=30")
            # Setting both the host and timeout to different values to improve success rate on unreachable ntp server
            ntptime.host = '2.north-america.pool.ntp.org'
            ntptime.timeout = 30
            try:
                ntptime.settime() # set the rtc
            except:
                print("Fatal error attempting to ntp time sync, sleeping...")
                sleepnow()
        date_time = list(rtc.datetime())
        date_time[4] = date_time[4] + localtimeOffset
        date_time = tuple(date_time)
        rtc.datetime(date_time)
    localTimeStr = str(time.localtime())
    print("Current local time: %s" % localTimeStr)
    

# Function that puts the esp32 into deepsleep mode
def sleepnow():
    import machine
        
    # put the device to sleep
    print("Debug: Going to Sleep")
    machine.deepsleep(60000)
    # After wake from deepsleep state, boots and runs boot.py, main.py
    # This script is generally saved as main.py on esp32 spiflash filesystem
    
    
# Function which connects to WiFi
# More info here: https://docs.micropython.org/en/latest/esp8266/tutorial/network_basics.html
def do_connect():
    import network
    import btree

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        # Assumes that btree database with 'wifi_data' filename exists with these two values
        f = open("wifi_data", "r+b")
        db = btree.open(f)
        ssid = db[b"SSID"]
        password = db[b"password"]
        # Always close your db and files *before* actions that could fail (network,etc.)
        db.close()
        f.close()
        print("connecting to network...")
        sta_if.active(True)
        sta_if.connect(ssid, password)
        while not sta_if.isconnected():
            pass
    print("network config:", sta_if.ifconfig())

# Does a HTTP/HTTPS GET request
# More info here: https://docs.micropython.org/en/latest/esp8266/tutorial/network_tcp.html
def http_get(url):
    import usocket
    import ussl

    res = ""
    scheme, _, host, path = url.split("/", 3)
    #print("scheme: %s, host: %s, path: %s" % (scheme, host, path))
    #print("url: %s" % url)
    
    if scheme == 'https:':
        port = 443
    elif scheme == 'http:':
        port = 80
    else:
        raise ValueError("Unsupported URI scheme (%s) in url (%s), only http/https supported" % (scheme,url))
    
    ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
    ai = ai[0]
    s = usocket.socket(ai[0], ai[1], ai[2])
    try:
        s.connect(ai[-1])
    except:
        print("Failed to connect, retrying...")
        time.sleep(10)
        s.connect(ai[-1])
    
    if scheme == "https:":
        try:
            s = ussl.wrap_socket(s, server_hostname=host)
        except: 
            s = ussl.wrap_socket(s, server_hostname=host)
        
    buffer =  "GET /%s HTTP/1.0\r\n" % (path)
    buffer += "Host: %s\r\n" % (host)
    buffer += "User-Agent: micropython/1.2.0 exampleweather esp32\r\n"
    buffer += "Accept: application/geo+json\r\n"
    # HTTP requests must end in an extra CRLF (aka \r\n)
    buffer += "\r\n"
#    print("Debug HTTP REQUEST: \r\n%s" % (buffer))
    
    s.write(bytes(buffer, "utf8"))
    while True:
        data = s.read(1000)
        #print("data: %s" % str(data))
        if data:
            res += str(data, "utf8")
        else:
            break
    s.close()
    
    return res

def parseJSON(response):
    import json
    import time
    
    # Following code is currently very NOAA weather API specific, no attempt has been made to abstract here.
    HTTP_1 = response.find("HTTP/1.0")
    HTTP_RESULT = response.find(" 200 OK\r\n",7)
    if  HTTP_1 == 0 and HTTP_RESULT == 8:
        print("Found 'HTTP/1.0 200 OK' Response.")
    else:
        print("Fatal failure during HTTP GET (%s), going to sleep..." % response.split("\n")[0])
        sleepnow()
        #raise ValueError("Web Server responded with failure code. (%s)" % response.split("\n")[0])
    jsondata = ""
    # BUG: Hacky way to parse through raw HTTP socket response and remove all non-JSON data
    for x in response.split("\n"):
        if (x.find("{") >= 0 or x.find("}") >= 0 or x.find("\":") >= 0 or x.find("]") >= 0 or x.find("[") >= 0):
            jsondata += x
            #print("MATCH Line: %s" % x)
        #else:
        #    print("NOMATCH Line: %s" % x)
    #print("jsondata: BEGIN---\r\n%s\r\nEND---" % jsondata)
    jsonelements = json.loads(jsondata)
    #print(jsonelements["properties"])
    jsonproperties = jsonelements["properties"]
    #print("Updated: %s" % jsonproperties["updated"])
    #print("Detailed Forecast: %s" % jsonproperties["periods"][1]["detailedForecast"])
    timehour = str(time.localtime()[3])
    timeminute = str(time.localtime()[4])
    displaytext = "Current Time: " + timehour + ":" + timeminute + "  "

    displaytext +=  "Updated Data: %s\n\n" % jsonproperties["updated"]

    ################ NOAA JSON DATA ##########################################
    #Period 0 is Current period, 1 is +12 hours, etc.
    #dict has members:
    #   "name": "Saturday Night",
    #   "startTime": "2023-07-22T18:00:00-04:00",
    #   "endTime": "2023-07-23T06:00:00-04:00",
    #   "isDaytime": false,
    #   "temperature": 65,
    #   "temperatureUnit": "F",
    #   "temperatureTrend": null,
    #   "probabilityOfPrecipitation": {
    #       "unitCode": "wmoUnit:percent",
    #       "value": null },
    #   "dewpoint": {
    #       "unitCode": "wmoUnit:degC",
    #       "value": 17.222222222222221 },
    #   "relativeHumidity": {
    #       "unitCode": "wmoUnit:percent",
    #       "value": 84 },
    #   "windSpeed": "6 to 10 mph",
    #   "windDirection": "NW",
    #   "icon": "https://api.weather.gov/icons/land/night/tsra_hi/few?size=medium",
    #   "shortForecast": "Slight Chance Showers And Thunderstorms then Mostly Clear",
    #   "detailedForecast": "A slight chance of showers and thunderstorms before 8pm. Mostly clear, with a low around 65."
    ################################################################################

    # Current Period
    pnum = 0
    displaytext += "Period: %s\n" % jsonproperties["periods"][pnum]["name"]
    displaytext += "Temperature: %s %s\n" % (jsonproperties["periods"][pnum]["temperature"],jsonproperties["periods"][pnum]["temperatureUnit"])
    displaytext += "Humidity: %s\n" % jsonproperties["periods"][pnum]["relativeHumidity"]["value"]
    displaytext += "Wind: %s at %s\n" % (jsonproperties["periods"][pnum]["windDirection"],jsonproperties["periods"][pnum]["windSpeed"])
    displaytext += "Forecast: %s\n\n" % jsonproperties["periods"][pnum]["shortForecast"]

    #Period++
    pnum +=1
    displaytext += "Period: %s\n" % jsonproperties["periods"][pnum]["name"]
    displaytext += "Temperature: %s %s\n" % (jsonproperties["periods"][pnum]["temperature"],jsonproperties["periods"][pnum]["temperatureUnit"])
    displaytext += "Humidity: %s\n" % jsonproperties["periods"][pnum]["relativeHumidity"]["value"]
    displaytext += "Wind: %s at %s\n" % (jsonproperties["periods"][pnum]["windDirection"],jsonproperties["periods"][pnum]["windSpeed"])
    displaytext += "Forecast: %s\n\n" % jsonproperties["periods"][pnum]["shortForecast"]

    #Period++
    pnum += 1
    displaytext += "Period: %s\n" % jsonproperties["periods"][pnum]["name"]
    displaytext += "Temperature: %s %s\n" % (jsonproperties["periods"][pnum]["temperature"],jsonproperties["periods"][pnum]["temperatureUnit"])
    displaytext += "Humidity: %s\n" % jsonproperties["periods"][pnum]["relativeHumidity"]["value"]
    displaytext += "Wind: %s at %s\n" % (jsonproperties["periods"][pnum]["windDirection"],jsonproperties["periods"][pnum]["windSpeed"])
    displaytext += "Forecast: %s\n\n" % jsonproperties["periods"][pnum]["shortForecast"]

    #Period++
    pnum += 1
    displaytext += "Period: %s\n" % jsonproperties["periods"][pnum]["name"]
    displaytext += "Temperature: %s %s\n" % (jsonproperties["periods"][pnum]["temperature"],jsonproperties["periods"][pnum]["temperatureUnit"])
    displaytext += "Humidity: %s\n" % jsonproperties["periods"][pnum]["relativeHumidity"]["value"]
    displaytext += "Wind: %s at %s\n" % (jsonproperties["periods"][pnum]["windDirection"],jsonproperties["periods"][pnum]["windSpeed"])
    displaytext += "Forecast: %s\n\n" % jsonproperties["periods"][pnum]["shortForecast"]
    
    return displaytext

    
def __init__():
    import machine
    import esp
    esp.osdebug(None)
    # Set speed to something slower than full speed to save power.
    machine.freq(80000000)
    reset_cause = machine.reset_cause()

    if reset_cause == machine.DEEPSLEEP_RESET:
        print("Woke up from a deep sleep")
    elif reset_cause == machine.PWRON_RESET:
        print("Power-on or Reset")
    elif reset_cause == machine.HARD_RESET:
        print("Hard Reset")
    elif reset_cause == machine.SOFT_RESET:
        print("Soft Reset")
    else:
        print("Unknown reset cause: %d" % machine.reset_cause())

    print("Wake Reason: %d" % machine.wake_reason())
    
    do_connect()
    setup_rtc()
    
    
    

def main():
    from soldered_inkplate10 import Inkplate
    
    #print ("Debug: Starting fetching data")
    #response = http_get("http://micropython.org/ks/test.html")
    # If you were to do a GET request to a different page, change the URL here
    
    # See https://www.weather.gov/documentation/services-web-api
    response = http_get("https://api.weather.gov/gridpoints/LWX/80%2C76/forecast")
    print ("Debug: Finished fetching data")
    
    displaytext = parseJSON(response)
    
    # Initialise our Inkplate object
    display = Inkplate(Inkplate.INKPLATE_1BIT)
    display.begin()
    # Make a copy of the framebuffer
    display.ipp.start()
    # Get display temperature from built-in sensor, requires calling display.display() or display.einkOn() first.  .display() is slow, use .einkOn()
    display.einkOn()
    temperature_C = display.readTemperature()
    print ("Debug: Finished reading temperature sensor.")
    temperature_F = (temperature_C * 1.8) + 32
    inside_temp = str(temperature_F)  
    #print("inside temp: %s" % inside_temp)
    displaytext += "Current Inside Temperature: %s F\n" % inside_temp

    #rotation int 0 = none 1 = 90deg clockwise rotation, 2 = 180deg, 3 = 270deg
    display.setRotation(0)
    
    #if you start getting bleeding on the display due to killing power during a draw operation, uncomment these two lines temporarily, or execute out of band of this script.
    #display.clearDisplay()
    #display.display()

    # Set font size
    display.setTextSize(3)

    # Print response in lines
    cnt = 0
    for x in displaytext.split("\n"):
        display.printText(
            10, 28 + cnt, x
        )  # Default font has only upper case letters
        cnt += 28
    print ("Debug: Starting final render on display.")
    # Actually update display with new data
    # display.display() is slow, use display.partialUpdate() when possible
    # 
    display.display()
    #display.partialUpdate()
    display.einkOff()
    # Deep Sleep
    sleepnow()


# Start of script

__init__()
main()
