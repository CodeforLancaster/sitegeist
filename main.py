import argparse
import os
import platform
import subprocess
import threading
import urllib.request
import zipfile

import api
import core.analyser as analyser
from core.domain import Database


def main():
    parser = argparse.ArgumentParser(description='SiteGeist: Analysing twitter sentiment in a geofenced area.')

    parser.add_argument('-g', '--geofence', nargs='+', type=float)
    parser.add_argument('-t', '--twitter-api-keys', nargs=4, type=str)

    args = parser.parse_args()

    locations = args.geofence
    keys = args.twitter_api_keys

    validate_lat_long(locations[0], locations[1])
    validate_lat_long(locations[2], locations[3])

    ta = analyser.TweetAnalyser(locations[0], locations[1], locations[2], locations[3],
                                consumer_key=keys[0], consumer_secret=keys[1], access_token_key=keys[2],
                                access_token_secret=keys[3])

    # start web front end
    api.start(Database.instance, ta)


def validate_lat_long(lat, long):
    if lat > 90 or lat < -90:
        raise Exception('Latitude ranges from -90 to 90. (%d)' % lat)

    if long > 180 or long < -180:
        raise Exception('Longitude ranges from -180 to 180. (%d)' % long)


if __name__ == '__main__':
    main()
