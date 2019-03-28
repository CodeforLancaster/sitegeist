# -*- coding: utf-8 -*-
"""
Created on Thu Nov  8 13:42:15 2018

@author: willf

Within this file are the bones of a basic Active Record style database API, which deals with the persistence of twitter
users, tweets and subjects.
"""

from datetime import datetime
import math
import numbers
import os
import re
import sqlite3
import time
from enum import Enum


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
        self.conn.execute('pragma journal_mode=wal')
        self.users = UserRepo(self)
        self.tweets = TweetRepo(self)
        self.subjects = SubjectRepo(self)

    def setup(self):
        print('Creating database')
        self.connect()
        schema = '%s %s %s' % (User.sql, Tweet.sql, Subject.sql)
        self.conn.executescript(schema)

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


class Entity:
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

    WORD = 0
    HASHTAG = 1
    MENTION = 2
    ALL = -1


class Subject:
    """
    Active record representing a tweet subject.
    """

    sql = '''CREATE TABLE IF NOT EXISTS subjects (subject text PRIMARY KEY NOT NULL, type INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS 
    tweet_subjects (tweet_id INTEGER, subject text, FOREIGN KEY (tweet_id) REFERENCES tweets(tweet_id), FOREIGN KEY (
    subject) REFERENCES subjects(subject)) '''

    def __init__(self, subject, subject_type: SubjectType, db=Database.instance):
        self.subject = subject
        self.db = db
        self.subject_type = subject_type

    @staticmethod
    def map_subject(row):
        if row is None:
            return None
        return Subject(subject=row[0], subject_type=SubjectType(int(row[1])))


class Tweet(Entity):
    """
    Active record representing a tweet.
    """

    sql = '''CREATE TABLE IF NOT EXISTS tweets (id INTEGER PRIMARY KEY, user_id INTEGER, tweet VARCHAR, sentiment INTEGER, 
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

    def hashtags_and_mentions(self):
        hashtags = re.findall('([#][\w_-]+)', self.tweet)
        mentions = re.findall('([@][\w_-]+)', self.tweet)

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

    BASE_QUERY = '''SELECT s.subject, s.type, sum(t.sentiment) as sum, count(*) as total, avg(t.sentiment) as avg, 
    (avg(t.sentiment) + 2) / 4 as scaled_avg
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

    def exists(self, subject: str):
        c = self.db.conn.cursor()
        c.execute('SELECT count(*) FROM subjects s WHERE s.subject = ?;', [subject])

        return c.fetchone()[0] > 0
