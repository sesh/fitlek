import json as json_lib
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler, HTTPSHandler, HTTPCookieProcessor
from collections import namedtuple
from http.cookiejar import CookieJar


def mmss_to_seconds(s):
    parts = s.split(":")

    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    else:
        raise Exception("Invalid duration provided, must use mm:ss format")


def seconds_to_mmss(seconds):
    mins = int(seconds / 60)
    seconds = seconds - mins * 60
    return f"{mins:02}:{seconds:02}"


def pace_to_ms(pace):
    seconds = mmss_to_seconds(pace)
    km_h = 60 / (seconds / 60)
    return km_h * 0.27778
