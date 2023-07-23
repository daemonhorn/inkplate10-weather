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
            print("Transient error setting the time from ntp, retrying with timeout=10")
            # Setting both the host and timeout to different values to improve success rate on unreachable ntp server
            ntptime.host = '2.north-america.pool.ntp.org'
            ntptime.timeout = 10
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
    do_connect("Down")
    print("Debug: Going to Sleep")
    machine.deepsleep(60000)
    # After wake from deepsleep state, boots and runs boot.py, main.py
    # This script is generally saved as main.py on esp32 spiflash filesystem
    
    
# Function which connects to WiFi
# More info here: https://docs.micropython.org/en/latest/esp8266/tutorial/network_basics.html
def do_connect(stateDesired = "Up"):
    import network
    import btree
    countrycode = "US" # https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
    hostname = "ink10-esp32-mpy" # Used during DHCP request, maximum 15 bytes for some reason
    wifi_phymode = network.MODE_11N # https://docs.micropython.org/en/latest/library/network.html#network.phy_mode

    network.country(countrycode)
    network.hostname(hostname)
    network.phy_mode(wifi_phymode)
    sta_if = network.WLAN(network.STA_IF)

    if stateDesired == "Down":
        print("Debug: Disconnecting WLAN")
        return sta_if.disconnect()

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
    import usocket as socket
    import ussl as ssl
    af = socket.AF_INET
    proto = socket.IPPROTO_TCP
    socktype = socket.SOCK_STREAM
    socket_timeout = 10 # seconds

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
    
    for addressinfo in socket.getaddrinfo(host, port, af, socktype, proto):
        af, socktype, proto, cname, sockaddr = addressinfo
        #print(".getaddrinfo() complete: (%s)" % str(addressinfo))
        try:
            s = socket.socket(af, socktype, proto)
        except OSError as msg:
            s = None
            continue
        s.settimeout(socket_timeout)
        try:
            s.connect(sockaddr)
        except OSError as msg:
            s.close()
            s = None
            continue
        break
    if s is None:
        print("Failed to connect, Going to sleep...")
        sleepnow()
    
    if scheme == "https:":
        try:
            s = ssl.wrap_socket(s, server_hostname=host)
        except: 
            print("Failed to wrap socket in ssl, Going to sleep...")
            sleepnow()
        
    buffer =  "GET /%s HTTP/1.0\r\n" % (path)
    buffer += "Host: %s\r\n" % (host)
    buffer += "User-Agent: micropython/1.2.0 exampleweather esp32\r\n"
    buffer += "Accept: application/geo+json\r\n"
    # HTTP requests must end in an extra CRLF (aka \r\n)
    buffer += "\r\n"
#    print("Debug HTTP REQUEST: \r\n%s" % (buffer))
    try:
        s.write(bytes(buffer, "utf8"))
    except:
        print("Failed to send GET request, Going to sleep...")
        sleepnow()
    while True:
        try:
            data = s.read(1000)
        except:
            sleepnow()
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
        print("Debug: 'HTTP/1.0 200 OK' Response.")
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
    timehour = time.localtime()[3]
    timeminute = time.localtime()[4]
    timeminuteStr = str(timeminute)
    if timehour > 12:
        timehour -= 12
        timesuffix = "pm"
    elif timehour == 0:
        timehour = 12;
        timesuffix = "am"
    else:
        timesuffix = "am"
    if len(timeminuteStr) < 2:
        timeminuteStr = "0" + timeminuteStr
    timehourStr = str(timehour)
    displaytext = "Current Time: " + timehourStr + ":" + timeminuteStr + " " + timesuffix + " "

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
    #machine.freq(80000000)
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
    return reset_cause  # pass this on to caller so that it can be referenced later
    
    

def main(reset_cause):
    from soldered_inkplate10 import Inkplate
    import machine
    
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

    #if you start getting bleeding on the display due to killing at the wrong, time just power cycle and will do a clearDisplay() then display()
    if reset_cause == machine.PWRON_RESET:
        print("Debug: Clearing Display of artifacts after power on")
        display.fillScreen(1)
        display.clearDisplay()
        display.display()
        display.clean()

    # Make a copy of the framebuffer
    #display.ipp.start()
    # Get display temperature from built-in sensor, requires calling display.display() or display.einkOn() first.  .display() is slow, use .einkOn()
    display.einkOn()
    temperature_C = display.readTemperature()
    print ("Debug: Finished reading temperature sensor.")
    temperature_F = (temperature_C * 1.8) + 32
    inside_temp = str(temperature_F)
    battery = display.readBattery()
    #print("inside temp: %s" % inside_temp)
    displaytext += "Current Inside Temperature: %s F  " % inside_temp
    displaytext += "Battery Voltage: %s" % str(battery)
    #rotation int 0 = none 1 = 90deg clockwise rotation, 2 = 180deg, 3 = 270deg
    display.setRotation(0)
    
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

main(__init__())
