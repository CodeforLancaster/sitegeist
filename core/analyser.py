# -*- coding: utf-8 -*-
import threading

import twitter
from pycorenlp import StanfordCoreNLP
from twitter import TwitterError

from core.domain import *


def compute_sentiment(res):
    snt = 0  # Neutral

    desc = ''

    for s in res["sentences"]:
        strength = int(s["sentimentValue"])

        desc += '(%d) ' % (strength - 2)

        snt = snt + (strength - 2)

    return snt, desc


class TweetAnalyser:
    def __init__(self, lat1, long1, lat2, long2, consumer_key, consumer_secret, access_token_key, access_token_secret,
                 nlp_url='http://localhost:9000'):

        self.access_token_secret = access_token_secret
        self.access_token_key = access_token_key
        self.consumer_secret = consumer_secret
        self.consumer_key = consumer_key
        self.nlp_url = nlp_url
        self.locations = ["%f,%f" % (long1, lat1), "%f,%f" % (long2, lat2)]
        self.locations_arr = [[lat1, long1], [lat2, long2]]

        print("Starting analyser daemon...")
        self.init()
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()

    def init(self):
        self.nlp = StanfordCoreNLP(self.nlp_url)
        self.db = Database()

        self.users = self.db.users
        self.tweets = self.db.tweets
        self.subjects = self.db.subjects

        self.api = twitter.Api(consumer_key=self.consumer_key,
                       consumer_secret=self.consumer_secret,
                       access_token_key=self.access_token_key,
                       access_token_secret=self.access_token_secret,
                       cache=None,
                       tweet_mode='extended')


    # This loads the most comprehensive text portion of the tweet
    # Where "data" is an individual tweet, treated as JSON / dict
    @staticmethod
    def get_text(tweet):
        # Try for extended text of original tweet, if RT'd (streamer)
        try:
            text = tweet['retweeted_status']['extended_tweet']['full_text']
        except:
            # Try for extended text of an original tweet, if RT'd (REST API)
            try:
                text = tweet['retweeted_status']['full_text']
            except:
                # Try for extended text of an original tweet (streamer)
                try:
                    text = tweet['extended_tweet']['full_text']
                except:
                    # Try for extended text of an original tweet (REST API)
                    try:
                        text = tweet['full_text']
                    except:
                        # Try for basic text of original tweet if RT'd
                        try:
                            text = tweet['retweeted_status']['text']
                        except:
                            # Try for basic text of an original tweet
                            try:
                                text = tweet['text']
                            except:
                                # Nothing left to check for
                                text = ''
        return text

    def process_tweet(self, tweet):

        if self.tweets.exists(tweet['id']):
            return

        text = self.get_text(tweet)
        res = self.annotate(text)

        if type(res) is str:
            print('Timed out.')
            return None

        uname = tweet['user']['name']

        user = self.get_user(uname)

        sentiment, desc = compute_sentiment(res)

        t = self.tweets.create(
            Tweet(_id=tweet['id'], user=user, sentiment=sentiment, tweet=text, time=tweet['created_at']))

        self.extract_subjects(res, t)

        reply = tweet['in_reply_to_status_id'] is not None
        quote = tweet['is_quote_status']

        if reply or quote:
            self.process_reply_or_quote(tweet)

        return t

    def process_reply_or_quote(self, tweet):
        try:
            tid = tweet['quoted_status_id'] if tweet['is_quote_status'] else tweet['in_reply_to_status_id']

            tp = None
            if not self.tweets.exists(tid):
                parent = self.api.GetStatus(status_id=tid)

                text = self.get_text(parent)

                resp = self.annotate(text)
                psen, desc = compute_sentiment(resp)
                tp = self.tweets.create(
                    Tweet(_id=tid, user=self.get_user(parent.user.screen_name), sentiment=psen,
                          tweet=text,
                          time=parent.created_at))
            else:
                tp = self.tweets.find_one(tid)
                resp = self.annotate(tp.tweet)

            # Extract subjects from reply or quoted tweet
            self.extract_subjects(resp, tp)
        except TwitterError as te:
            print(te.message)

        return tweet

    def run(self):
        for tweet in self.api.GetStreamFilter(locations=self.locations):

            try:
                entity = self.process_tweet(tweet)
            except Exception as e:
                print(e)
                continue

            if entity is None:
                continue

            print('@' + entity.user.name + ': ' + self.get_text(tweet))
            print("Sentiment = %d" % entity.sentiment)

    def get_user(self, uname):
        if not self.users.exists(uname):
            user = self.users.create(User(uname, self.db))
        else:
            user = self.users.find_by_name(uname)

        return user

    def annotate(self, text):
        return self.nlp.annotate(text,
                                 properties={
                                     'annotators': 'tokenize,ssplit,lemma,parse,sentiment,pos,ner',
                                     'outputFormat': 'json',
                                     'timeout': 1500,
                                 })

    def extract_subjects(self, res, tweet):
        for sentence in res['sentences']:
            entities = [x['text'] for x in sentence['entitymentions']]

            for entity in entities:
                if entity.startswith('#') or entity.startswith('@'):
                    continue

                self.subjects.create(entity, tweet, SubjectType.WORD)

        hashtags, mentions = tweet.hashtags_and_mentions()

        [self.subjects.create(hashtag, tweet, SubjectType.HASHTAG) for hashtag in hashtags]
        [self.subjects.create(mention, tweet, SubjectType.MENTION) for mention in mentions]
