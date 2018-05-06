#!/usr/bin/env python

"""
wezzer.py
it's wezzer, for weather
github.com/nqnzp/wezzer
"""

from __future__ import print_function

import argparse
import datetime
from dateutil.parser import parse
from geoip import geolite2
from geopy.geocoders import Nominatim
import ipgetter
import json
import requests
import sys
from termcolor import colored, cprint
import textwrap
from pprint import pprint


# A handful of really short function definitions
# All of them return... things

def get_localhost_ip():
    myip = ipgetter.myip()
    return str(myip)     # returns a string of format "0.0.0.0"


def get_geoip(ip_addr):
    match = geolite2.lookup(ip_addr)
    return (match)  # returns a geoip object


def get_geopy_zip(zip):
    geo = Nominatim()
    loc = geo.geocode(zip)
    return (loc)  # returns a geopy object

def get_geopy_city(city):
    geo = Nominatim()
    loc = geo.geocode(city)
    return (loc)  # returns a geopy object


def get_endpoint_data(geolocation):
    try:
        r = requests.get("https://api.weather.gov/points/%s" % geolocation)
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if r.status_code == 404:
            print ("Error: Invalid address, city, or zip code provided.")
        sys.exit(1)

    if r.status_code == 200:
        endpoint_data = json.loads(r.content)
    else:
        print("Error: Failed to get response from weather.gov API")

    return endpoint_data  # returns a json object


def get_forecast_data(forecast_url):
    response = requests.get(forecast_url)

    if response.status_code == 200:
        forecast_data = json.loads(response.content)
    else:
        print("[*] Failed to get response from API")

    return forecast_data  # returns a json object


def add_args(parser):
    parser.add_argument('-c', '--color',
                        action="store_true",
                        dest="color_on",
                        help="Enable terminal colors",
                        default=False)
    parser.add_argument('-d', '--days',
                        action="store",
                        dest="num_days",
                        help="Number of days for Extended Forecast",
                        default=2, type=int)
    parser.add_argument('-t', '--hours',
                        action="store",
                        dest="num_hours",
                        help="Number of hours for Hourly Forecast",
                        default=12, type=int)
    parser.add_argument('-w', '--width',
                        action="store",
                        dest="column_width",
                        help="Max width of the output (default 80 columns)",
                        default=80, type=int)
    parser.add_argument('-z', '--zipcode',
                        action="store", dest="zip_code",
                        help="ZIP Code of desired weather location", type=str)
    return parser


"""
========= MAIN ========
"""

if __name__ == "__main__":

    # The most important variable declaration
    version = "Wezzer 0.1.1"

    # Parsing some args from the command line. Neal Stephenson would be proud.
    parser = argparse.ArgumentParser()
    parser = add_args(parser)
    results = parser.parse_args()

    # Initialize our variables off the arparser
    extended_default = results.num_days * 2
    hourly_default = results.num_hours
    hourly_default_str = str(results.num_hours)
    color_on = results.color_on
    zip_code = results.zip_code

    # Setting up the textwrapper object
    indstr = "    "
    wrapper = textwrap.TextWrapper()
    wrapper.width = results.column_width
    wrapper.initial_indent = indstr
    wrapper.subsequent_indent = indstr


    # Make a datetime object for right now's time
    d = datetime.datetime.now()
    nowtime = d.strftime("%Y-%m-%d %I:%M %p")

    # If the user provides a zip code, look up the lat/long for
    # that, otherwise use their IP address
    if zip_code:
        geopy = get_geopy_zip(zip_code)
        latlong_str = str(geopy.latitude) + "," + str(geopy.longitude)

    else:
        # Determine the IP address of the host running the script
        ip_addr = get_localhost_ip()

        # Determine the latitude and longitude of the IP address
        geoip = get_geoip(ip_addr)
        location = geoip.location

        # Convert the geoip tuple to a string to use it
        # in the API request
        latlong_str = str(location[0]) + "," + str(location[1])

    # Send API request to weather.gov to get the
    # endpoint location data

    epdata = get_endpoint_data(latlong_str)

    # Derive the URLs from the returned endpoint data
    forecast_url = epdata["properties"]["forecast"]
    hourly_url = epdata["properties"]["forecastHourly"]

    # Use the forecast and hourly forecast URLs to get
    # forecast and hourly data
    forecast_data = get_forecast_data(forecast_url)
    hourly_data = get_forecast_data(hourly_url)

    # Find the city and state from the returned endpoint data
    city = epdata["properties"]["relativeLocation"]["properties"]["city"]
    state = epdata["properties"]["relativeLocation"]["properties"]["state"]

    # Setup variable for temperature trend monitoring
    last_temp = 0

    # The color handling logic is not the greatest
    if color_on:
        version = colored(version, 'yellow')
        nowtime = colored(nowtime, 'yellow')
        hourly_default_str = colored(hourly_default_str + "-Hour Forecast", 'yellow')
    else:
        hourly_default_str = hourly_default_str + "-Hour Forecast"

    print("\n" + version)
    print("Weather for %s, %s (%s)" % (city, state, nowtime))
    print("\n" + hourly_default_str)

    # Iterate through the hourly JSON, print
    # the time, temp, and forecast

    for period in hourly_data["properties"]["periods"]:

        # pprint(period)

        # Limit the output to what was set on
        # command line or default
        if period["number"] > hourly_default:
            break

        # Convert the formatted time to a datetime object
        start_d = parse(period["startTime"])
        end_d = parse(period["endTime"])

        # Output just the hour and minute
        start_time = start_d.strftime("%I:%M %p")
        end_time = end_d.strftime("%I:%M %p")

        # Get trend information on the temperature
        this_temp = int(period["temperature"])
        temperature = str(period["temperature"])

        if color_on:
            if last_temp == 0:
                trend = colored(u'\u25aa')
            elif last_temp < this_temp:
                trend = colored(u'\u25b2', 'red')
            elif last_temp > this_temp:
                trend = colored(u'\u25bc', 'blue')
            else:
                trend = colored(u'\u25aa', 'yellow')

            start_time = colored(start_time, 'cyan')
            end_time = colored(end_time, 'cyan')
            temperature = colored(temperature, attrs=['bold'])
        else:
            if last_temp == 0:
                trend = u'\u25aa'
            elif last_temp < this_temp:
                trend = u'\u25b2'
            elif last_temp > this_temp:
                trend = u'\u25bc'
            else:
                trend = u'\u25aa'

        last_temp = this_temp

        # Print some output of the time, temperature and short forecast
        print (start_time + ' - ' + end_time + ' ', end='')
        print (trend + " ", end='')
        print (temperature, end='')
        print (period["temperatureUnit"] + " ", end='')
        print (period["shortForecast"], end='')
        print (", wind " + period["windSpeed"] + " " + period["windDirection"])

    # Print a nice message about the x-Day forecast
    if color_on:
        cprint("\n" + str(results.num_days) +
               "-Day Extended Forecast", 'yellow')
    else:
        print("\n" + str(results.num_days) + "-Day Extended Forecast")

    # Iterate through the forecast JSON and print
    # the name and forecast
    for period in forecast_data["properties"]["periods"]:

        if period["number"] > extended_default:
            break

        #pprint(period)

        unit = period["temperatureUnit"]

        if color_on:
            name = colored(period["name"] + ": ", 'cyan')
            if period["temperatureTrend"] == "falling":
                trend = colored(u'\u25bc', 'blue')
            elif period["temperatureTrend"] == "rising":
                trend = colored(u'\u25b2', 'red')
            else:
                trend = colored(u'\u25aa')
            temp = colored(str(period["temperature"]), attrs=['bold'])
        else:
            name = period["name"] + ": "
            temp = str(period["temperature"])
            if period["temperatureTrend"] == "falling":
                trend = u'\u25bc'
            elif period["temperatureTrend"] == "rising":
                trend = u'\u25b2'
            else:
                trend = u'\u25aa'

        print(name + trend + " " + temp + unit)

        # Use text wrap to limit the output to x characters wide
        print(wrapper.fill(period["detailedForecast"]))