# -*- coding: utf-8 -*-
"""
Created on Thu Nov  8 13:42:15 2018

@author: willf

Within this file are the bones of a basic Active Record style database API, which deals with the persistence of twitter
users, tweets and subjects.
"""

import math
import numbers
import os
import re
import sqlite3
import time
from datetime import datetime
from enum import Enum


class StdevFunc:
    def __init__(self):
        self.M = 0.0
        self.S = 0.0
        self.k = 1

    def step(self, value):
        if value is None:
            return
        tM = self.M
        self.M += (value - tM) / self.k
        self.S += (value - tM) * (value - self.M)
        self.k += 1

    def finalize(self):
        if self.k < 3:
            return None
        return math.sqrt(self.S / (self.k-2))


class Database:
    """
    Wrapper class for the SQLite database. Abstracts connection, creation and bootstrapping of the repository classes.
    """
    instance = None

    def __init__(self, path='tweets.db'):
        self.path = path
        self.users = None
        self.tweets = None
        self.subjects = None
        self.conn = None

        exists = os.path.isfile(self.path)
        self.connect()
        if not exists:
            self.setup()

        Database.instance = self

    def __del__(self):
        if self.conn is not None:
            print('Closing db connection')
            self.conn.close()

    def connect(self):
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.create_aggregate("stdev", 1, StdevFunc)
        self.conn.execute('pragma journal_mode=wal')
        self.users = UserRepo(self)
        self.tweets = TweetRepo(self)
        self.subjects = SubjectRepo(self)

    def setup(self):
        print('Creating database')
        self.connect()

        for ct in [User.sql, Tweet.sql, Subject.sql, SubjectSummary.sql]:
            print('Executing: %s' % ct)
            self.conn.executescript(ct)

    def recreate(self):
        self.__del__()
        os.remove(self.path)
        self.setup()

    def commit(self):
        self.conn.commit()


def commit_after(func):
    """
    Decorator function that commits the current transaction after execution of the function.

    :param func: function to decorate
    :return:
    """

    def decorator_func(*args, **kwargs):
        # Invoke the wrapped function first
        retval = func(*args, **kwargs)
        # Now do something here with retval and/or action
        Database.instance.commit()
        return retval

    return decorator_func


class Serializable:
    def to_dict(self):
        return self.__dict__


class Entity(Serializable):
    """
    Base class for all entities, abstracts the ID property and the database self reference.
    """

    def __init__(self, _id=-1, db=Database.instance):
        self._id = _id
        self.db = db

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id):
        self._id = id

    def to_dict(self):
        data = super(Entity, self).to_dict()
        del data['db']
        return data


class User(Entity):
    """
    Active record representing a twitter user.
    """

    sql = 'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name VARCHAR);'

    def __init__(self, name, _id=-1):
        super().__init__(_id)
        self.name = name

    def tweets(self):
        c = self.db.conn.cursor()
        c.execute('SELECT * FROM tweets t WHERE t.user_id = ?;', [self._id])
        return [self.map_tweet(row, user=self) for row in c.fetchall()]

    @staticmethod
    def map_user(row):
        if row is None:
            return None
        return User(_id=row[0], name=row[1])


class SubjectType(Enum):
    """
    Enumeration for the three types of tweet subjects - a word, a hashtag or a mention (username). It's important to
    draw this distinction so we can investigate mentions, hashtags and words separately.
    """

    ENTITY = 0
    HASHTAG = 1
    MENTION = 2
    PHRASE = 3
    ALL = -1


class Subject(Serializable):
    """
    Active record representing a tweet subject.
    """

    sql = '''CREATE TABLE IF NOT EXISTS subjects (subject text PRIMARY KEY NOT NULL, type INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS 
    tweet_subjects (tweet_id INTEGER, subject text, FOREIGN KEY (tweet_id) REFERENCES tweets(tweet_id), FOREIGN KEY (
    subject) REFERENCES subjects(subject));'''

    def __init__(self, subject, subject_type: SubjectType, db=Database.instance):
        self.subject = subject
        self.db = db
        self.subject_type = subject_type

    @staticmethod
    def map_subject(row):
        if row is None:
            return None
        return Subject(subject=row[0], subject_type=SubjectType(int(row[1])))


class SubjectSummary(Serializable):
    """
    Represents a summary of particular subject over 24 hours. This is used for maintaining records about trends over
    time.
    """

    sql = '''CREATE TABLE IF NOT EXISTS subject_summaries (subject TEXT NOT NULL, day DATE NOT NULL, 
    type INTEGER NOT NULL, num_tweets INTEGER NOT NULL, sum_sentiment REAL NOT NULL, avg_sentiment REAL NOT NULL, 
    PRIMARY KEY (subject, day));'''

    def __init__(self, subject, subject_type: SubjectType, num_tweets, sum_sentiment, avg_sentiment, day=datetime.now(),
                 db=Database.instance):
        self.subject = subject
        self.db = db
        self.subject_type = subject_type
        self.num_tweets = num_tweets
        self.sum_sentiment = sum_sentiment
        self.avg_sentiment = avg_sentiment
        self.day = day

    @staticmethod
    def map_subject_summary(row, user=None):
        return SubjectSummary(row[0], SubjectType(row[2]), row[4], row[3], row[5], row[1])

    def to_dict(self):
        data = super(SubjectSummary, self).to_dict()
        del data['db']
        return data


class Tweet(Entity):
    """
    Active record representing a tweet.
    """

    sql = '''CREATE TABLE IF NOT EXISTS tweets (id INTEGER PRIMARY KEY, user_id INTEGER, tweet VARCHAR, sentiment REAL, 
    time DATETIME, FOREIGN KEY (user_id) REFERENCES users(id)); '''

    def __init__(self, user: User, tweet, sentiment=None, _id=None, time=None):
        super().__init__(_id)
        if time is None:
            time = Tweet.time_to_str()
        elif isinstance(time, numbers.Number):
            if math.isnan(time):
                time = Tweet.time_to_str()
            else:
                time = Tweet.time_to_str(time)
        else:
            time = datetime.strptime(time, '%a %b %d %H:%M:%S %z %Y')

        self.user = user
        self.tweet = tweet
        self.sentiment = sentiment
        self.time = time
        self.hash_re = re.compile(r'\s([#][\w_-]+)')
        self.mention_re = re.compile(r'\s([@][\w_-]+)')

    def hashtags_and_mentions(self):
        hashtags = self.hash_re.findall(self.tweet)
        mentions = self.mention_re.findall(self.tweet)

        return hashtags, mentions

    @staticmethod
    def time_to_str(ts=time.time()):
        return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def map_tweet(row, user=None):
        return Tweet(_id=row[0], user=user, tweet=row[2], sentiment=row[3], time=row[4])


class TweetRepo:
    """
    Repository class for tweet-related database operations
    """

    def __init__(self, db):
        self.db = db

    def exists(self, _id):
        c = self.db.conn.cursor()
        c.execute('SELECT count(*) FROM tweets t WHERE t.id = ?;', [_id])

        return c.fetchone()[0] > 0

    @commit_after
    def create(self, tweet: Tweet):
        c = self.db.conn.cursor()
        c.execute('INSERT INTO tweets VALUES(?, ?, ?, ?, ?);',
                  [tweet.id, tweet.user.id, tweet.tweet, tweet.sentiment, tweet.time])
        tweet.id = c.lastrowid

        return tweet

    def delete_older_than_24h(self):
        c = self.db.conn.cursor()
        rows = c.execute("DELETE FROM tweets WHERE time <= date('now','-1 day')")
        return rows[0]

    def find_one(self, _id):
        c = self.db.conn.cursor()
        c.execute('SELECT * FROM tweets t WHERE t.id = ?;', [_id])
        tweet = c.fetchone()

        c.execute('SELECT * FROM users u WHERE u.id = ? LIMIT 1;', [tweet[1]])
        user = c.fetchone()

        return Tweet.map_tweet(tweet, User.map_user(user))


class UserRepo:
    """
    Repository class for user-related database operations
    """

    def __init__(self, db):
        self.db = db

    def find_all(self):
        c = self.db.conn.cursor()
        c.execute('SELECT * FROM users;')

        return [User.map_user(row) for row in c.fetchall()]

    def exists(self, name):
        c = self.db.conn.cursor()
        c.execute('SELECT count(*) FROM users u WHERE u.name = ?;', [name])

        return c.fetchone()[0] > 0

    def find_by_name(self, name):
        c = self.db.conn.cursor()
        c.execute('SELECT * FROM users u WHERE u.name = ? LIMIT 1;', [name])

        return User.map_user(c.fetchone())

    @commit_after
    def create(self, user: User):
        c = self.db.conn.cursor()
        c.execute('INSERT INTO users VALUES(NULL, ?);', [user.name])
        user.id = c.lastrowid
        return user


class SubjectRepo:
    """
    Repository class for subject-related database operations
    """

    BASE_QUERY = '''SELECT s.subject, s.type, sum(t.sentiment) as sum, count(*) as total, avg(t.sentiment) as avg
        FROM tweet_subjects ts 
        LEFT JOIN tweets t ON ts.tweet_id = t.id 
        LEFT JOIN subjects s on ts.subject = s.subject
        WHERE t.time >= date('now','-1 day')'''

    def __init__(self, db):
        self.db = db

    @commit_after
    def create(self, subject: str, tweet: Tweet, type: SubjectType):
        c = self.db.conn.cursor()
        if not self.exists(subject):
            c.execute('INSERT INTO subjects VALUES(?, ?);', [subject, type.value])

        c.execute('INSERT INTO tweet_subjects VALUES(?, ?);', [tweet.id, subject])
        return Subject(subject, type)

    def top(self, n=10, sort='asc', subj_type=SubjectType.ALL):
        c = self.db.conn.cursor()

        query = self.BASE_QUERY
        if subj_type != SubjectType.ALL:
            query = query + " AND s.type = %d" % subj_type.value

        c.execute(query +
                  " GROUP BY ts.subject ORDER BY sum %s, total %s LIMIT %d" % (sort, sort, n))
        return c.fetchall()

    def hot(self, n=10, sort='asc', subj_type=SubjectType.ALL):
        c = self.db.conn.cursor()

        query = self.BASE_QUERY
        if subj_type != SubjectType.ALL:
            query = query + " AND s.type = %d" % subj_type.value

        c.execute(query +
                  " GROUP BY ts.subject ORDER BY total %s LIMIT %d" % (sort, n))
        return c.fetchall()

    def trend(self, n=10, sort='asc', subj_type=SubjectType.ALL, trend_time=1):
        c = self.db.conn.cursor()
        subj = ''
        if subj_type != SubjectType.ALL:
            subj = '''AND s.type IS {}'''.format(subj_type.value)

        query = '''SELECT subject, type, sumSent, cnt, avgSent, (cnt  - mean) / std as zScore
                        FROM (
                            SELECT subject, type, AVG(cnt) AS mean, STDEV(cnt) as std, sumSent, avgSent, cnt, timeSep
                                FROM (
                                    SELECT
                                        s.subject, 
                                        s.type, 
                                        SUM(t.sentiment) AS sumSent, 
                                        COUNT(*) as cnt, 
                                        AVG(t.sentiment) AS avgSent,
                                        strftime('%H', time) as hourTime,
                                        CASE 
                                            WHEN DATETIME(time) >= DATETIME('now', '-{} hour')
                                            THEN 'NOW'
                                            ELSE 'BEFORE'
                                            END AS timeSep

                                    FROM tweet_subjects as ts
                                    LEFT JOIN tweets t ON ts.tweet_id = t.id 
                                    LEFT JOIN subjects s on ts.subject = s.subject
                                    WHERE t.time >= date('now','-1 day')
                                    {}
                                    GROUP BY s.subject, hourTime
                                    )
                                GROUP BY subject, timeSep
                                )
                        WHERE timeSep IS 'NOW' AND (zScore > 0 OR zScore IS NULL)
                        ORDER BY zScore {}, cnt {}
                        LIMIT {}
                    '''.format(trend_time, subj, sort, sort, n)

        c.execute(query)
        return c.fetchall()

    def summaries(self, days=7, limit=-1, sort='desc', at_least=1):
        c = self.db.conn.cursor()
        if not limit == -1:

            # In this case, we grab the top 'n' of each subject over the specified period.
            # SQLite doesn't have a nice native support for this sort of 'group by limit' query, so I just repeat
            # several small queries and aggregate the results.

            data = []

            while days > 1:
                q = """SELECT * from subject_summaries WHERE 
                day >= date('now','-%d days') and day <= date('now', '-%d days') 
                GROUP BY subject HAVING num_tweets > %d 
                ORDER BY num_tweets %s LIMIT %d;""" % (days, days - 1, at_least, sort, limit)
                c.execute(q)
                data = data + [SubjectSummary.map_subject_summary(row) for row in c.fetchall()]
                days = days - 1

            return data
        else:

            # In the alternative case, we just dump everything from summaries. This could be a LOT of data.

            q = """SELECT * from subject_summaries WHERE 
                day >= date('now','-%d days')
                GROUP BY subject HAVING num_tweets > %d 
                ORDER BY num_tweets %s LIMIT %d""" % (days, at_least, sort, limit)

            c.execute(q)
            return [SubjectSummary.map_subject_summary(row) for row in c.fetchall()]

    @commit_after
    def archive_last_24h(self):
        q = """INSERT INTO subject_summaries (subject, day, type, sum_sentiment, num_tweets, avg_sentiment) 
        SELECT s.subject, date('now', '-1 day'), s.type, sum(t.sentiment) as sum, count(ts.subject) as total, avg(t.sentiment)
        FROM tweet_subjects ts 
        LEFT JOIN tweets t ON ts.tweet_id = t.id 
        LEFT JOIN subjects s on ts.subject = s.subject
        WHERE t.time >= date('now','-1 day') GROUP BY ts.subject HAVING total > 1 ORDER BY total DESC;"""

        c = self.db.conn.cursor()
        c.execute(q)

    def exists(self, subject: str):
        c = self.db.conn.cursor()
        c.execute('SELECT count(*) FROM subjects s WHERE s.subject = ?;', [subject])

        return c.fetchone()[0] > 0
