# -*- coding: utf-8 -*-
import threading
import twitter
import spacy
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from twitter import TwitterError
from core.domain import *

pos_include = ['NOUN', 'PROPN']


class TweetAnalyser:
    def __init__(self, lat1, long1, lat2, long2, consumer_key, consumer_secret, access_token_key, access_token_secret):

        self.access_token_secret = access_token_secret
        self.access_token_key = access_token_key
        self.consumer_secret = consumer_secret
        self.consumer_key = consumer_key
        self.locations = ["%f,%f" % (long1, lat1), "%f,%f" % (long2, lat2)]
        self.locations_arr = [[lat1, long1], [lat2, long2]]
        self.nlp = spacy.load("en_core_web_sm")
        self.sentiment = SentimentIntensityAnalyzer()
        self.url_re = re.compile(r'http\S+')
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
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()

    def compute_sentiment(self, res):
        """
        TODO This could be a bit more nuanced. Rework later. Workaround to fit current metric
        :param res:
        :return:
        """
        snt = 0  # Neutral

        desc = ''

        for s in res.sents:
            sentiment = self.sentiment.polarity_scores(s.text)

            desc += '(%.2f) ' % sentiment['compound']

            snt += sentiment['compound']

        return snt, desc

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

        uname = tweet['user']['name']

        user = self.get_user(uname)

        sentiment, desc = self.compute_sentiment(res)

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
                psen, desc = self.compute_sentiment(resp)
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
            print("Sentiment = %.2f" % entity.sentiment)

    def get_user(self, uname):
        if not self.users.exists(uname):
            user = self.users.create(User(uname, self.db))
        else:
            user = self.users.find_by_name(uname)

        return user

    def annotate(self, text):

        return self.nlp(text)

    def extract_subjects(self, res, tweet):
        entities = [e.text.strip() for e in res.ents if (len(e.text.strip()) > 1) & ('http' not in e.text.strip())]
        print('Entities: {}'.format(entities))
        chunks = [c.text.strip() for c in res.noun_chunks if
                  (c.text.strip() not in entities) &
                  (len(c.text.strip()) > 1) &
                  (c.root.pos_ in pos_include) &
                  ('http' not in c.text.strip())]
        print('Chunks: {}'.format(chunks))
        entities += chunks
        for entity in entities:
            if entity.startswith('#') or entity.startswith('@'):
                continue
            self.subjects.create(entity, tweet, SubjectType.WORD)

        hashtags, mentions = tweet.hashtags_and_mentions()

        [self.subjects.create(hashtag, tweet, SubjectType.HASHTAG) for hashtag in hashtags]
        [self.subjects.create(mention, tweet, SubjectType.MENTION) for mention in mentions]
