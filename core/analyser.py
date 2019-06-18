# -*- coding: utf-8 -*-
import re
import threading
import json
import schedule
import spacy
import twitter
import emoji
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from twitter import TwitterError

from core.domain import *


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
        self.hash_re = re.compile(r'\s([#][\w_-]+)')
        self.mention_re = re.compile(r'\s([@][\w_-]+)')
        self.db = Database()
        self.users = self.db.users
        self.tweets = self.db.tweets
        self.subjects = self.db.subjects
        self._load_lists()
        schedule.every().day.at("00:00").do(self.job)

        self.api = twitter.Api(consumer_key=self.consumer_key,
                               consumer_secret=self.consumer_secret,
                               access_token_key=self.access_token_key,
                               access_token_secret=self.access_token_secret,
                               cache=None,
                               tweet_mode='extended')

        jobs_thread = threading.Thread(target=self.schedule_daemon, args=())
        jobs_thread.daemon = True
        jobs_thread.start()

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()

    def _load_lists(self):
        with open('./core/nlp_utils/include_phrase_pos.json', 'r', encoding='utf-8') as f:
            self.include_phrase_pos = json.loads(f.read())
            f.close()
        with open('./core/nlp_utils/exclude_tokens.json', 'r', encoding='utf-8') as f:
            self.exclude_tokens = json.loads(f.read())
            f.close()
        with open('./core/nlp_utils/include_word_pos.json', 'r', encoding='utf-8') as f:
            self.include_word_pos = json.loads(f.read())
            f.close()
        with open('./core/nlp_utils/include_entity_types.json', 'r', encoding='utf-8') as f:
            self.include_entity_types = json.loads(f.read())
            f.close()

    def job(self):
        self.subjects.archive_last_24h()

    @staticmethod
    def schedule_daemon(interval=1):
        while True:
            schedule.run_pending()
            time.sleep(interval)

    def compute_sentiment(self, res):
        """
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
        except KeyError:
            # Try for extended text of an original tweet, if RT'd (REST API)
            try:
                text = tweet['retweeted_status']['full_text']
            except KeyError:
                # Try for extended text of an original tweet (streamer)
                try:
                    text = tweet['extended_tweet']['full_text']
                except KeyError:
                    # Try for extended text of an original tweet (REST API)
                    try:
                        text = tweet['full_text']
                    except KeyError:
                        # Try for basic text of original tweet if RT'd
                        try:
                            text = tweet['retweeted_status']['text']
                        except KeyError:
                            # Try for basic text of an original tweet
                            try:
                                text = tweet['text']
                            except KeyError:
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

    def extract_entities(self, text):
        entities = []
        for e in text.ents:
            if (len(e.text) > 1) & ('http' not in e.text.lower()) & (e.label_ in self.include_entity_types):
                if e.text.startswith('#') or e.text.startswith('@'):
                    continue
                entities.append(e.text.strip())
        return entities

    def extract_phrases(self, text):
        phrases = []
        for ch in text.noun_chunks:
            cht = ch.text.strip()
            if (len(cht) > 1) & (ch.root.tag_ in self.include_phrase_pos) & ('http' not in cht) & (
                    ch.root.text.lower() not in self.exclude_tokens):
                if cht.startswith('#') or cht.startswith('@') or (len(cht.split()) == 1):
                    continue
                phrases.append(cht.lower())
        return phrases

    def hashtags_and_mentions(self, text):
        hashtags = self.hash_re.findall(text.text)
        mentions = self.mention_re.findall(text.text)
        return hashtags, mentions

    def extract_words(self, text):
        words = []
        for t in text:
            tl = t.text.lower()
            if (t.tag_ in self.include_word_pos) & (tl not in self.exclude_tokens) & (len(tl) > 1):
                if tl.startswith('#') or tl.startswith('@'):
                    continue
                words.append(tl)
        return words

    def extract_emojis(self, text):
        return [d['emoji'] for d in emoji.emoji_lis(text.text)]

    def extract_subjects(self, res, tweet):
        emojis = self.extract_emojis(res)
        hashtags, mentions = self.hashtags_and_mentions(res)
        entities = self.extract_entities(res)
        words = [w for w in self.extract_words(res) if w not in emojis + entities]
        phrases = [p for p in self.extract_phrases(res) if p not in entities]

        print('\tEntities: {}'.format(entities))
        print('\tWords: {}'.format(words))
        print('\tEmojis: {}'.format(emojis))
        print('\tPhrases: {}'.format(phrases))
        print('\tHashtags: {}'.format(hashtags))
        print('\tMentions: {}\n'.format(mentions))

        [self.subjects.create(entity, tweet, SubjectType.ENTITY) for entity in entities]
        [self.subjects.create(word, tweet, SubjectType.WORD) for word in words]
        [self.subjects.create(emoji, tweet, SubjectType.EMOJI) for emoji in emojis]
        [self.subjects.create(hashtag, tweet, SubjectType.HASHTAG) for hashtag in hashtags]
        [self.subjects.create(mention, tweet, SubjectType.MENTION) for mention in mentions]
        [self.subjects.create(phrase, tweet, SubjectType.PHRASE) for phrase in phrases]
