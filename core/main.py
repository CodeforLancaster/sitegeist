import argparse
import os
import platform
import subprocess
import threading
import urllib.request
import zipfile

import api
from core import analyser
from core.domain import Database


def main():
    parser = argparse.ArgumentParser(description='SiteGeist: Analysing twitter sentiment in a geofenced area.')

    parser.add_argument('-g', '--geofence', nargs='+', type=float)
    parser.add_argument('-t', '--twitter-api-keys', nargs=4, type=str)
    parser.add_argument('-s', '--nlp-server-url', nargs=1, type=str)

    args = parser.parse_args()

    locations = args.geofence
    keys = args.twitter_api_keys
    nlp_url = args.nlp_server_url

    validate_lat_long(locations[0], locations[1])
    validate_lat_long(locations[2], locations[3])

    if nlp_url is None:
        if not os.path.isdir("stanford-corenlp-full-2018-10-05"):
            print('Installing CoreNLP (this will take a while) ...')
            urllib.request.urlretrieve("http://nlp.stanford.edu/software/stanford-corenlp-full-2018-10-05.zip",
                                       "stanford-corenlp-full-2018-10-05.zip")
            zf = zipfile.ZipFile("stanford-corenlp-full-2018-10-05.zip", 'r')
            zf.extractall()
            zf.close()
            nlp = NLPServer()
    else:
        nlp_url = "http://localhost:9000"

    ta = analyser.TweetAnalyser(locations[0], locations[1], locations[2], locations[3],
                                consumer_key=keys[0], consumer_secret=keys[1], access_token_key=keys[2],
                                access_token_secret=keys[3],
                                nlp_url=nlp_url)

    # start web front end
    api.start(Database.instance, ta)


def validate_lat_long(lat, long):
    if lat > 90 or lat < -90:
        raise Exception('Latitude ranges from -90 to 90. (%d)' % lat)

    if long > 180 or long < -180:
        raise Exception('Longitude ranges from -180 to 180. (%d)' % long)


class NLPServer:
    def __init__(self):
        print('Starting Stanford NLP server...')
        thread = threading.Thread(target=self.start_nlp_server, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()

    @staticmethod
    def start_nlp_server():
        if platform.system() == 'Windows':
            subprocess.call(['runnlp.bat'])
        else:
            subprocess.call(['runnlp.sh'])


if __name__ == '__main__':
    main()
