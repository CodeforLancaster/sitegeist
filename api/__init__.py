import threading

from flask import Flask
from flask_injector import FlaskInjector
from injector import singleton

from api import rest, pages
from core import domain
from core.analyser import TweetAnalyser

app = Flask(__name__)


def start(db, ta):
    # Initialize Flask-Injector. This needs to be run *after* you attached all
    # views, handlers, context processors and template globals.
    app.register_blueprint(rest.bp)
    app.register_blueprint(pages.bp)

    def module(binder):
        binder.bind(
            domain.Database,
            to=db,
            scope=singleton,
        )
        binder.bind(
            TweetAnalyser,
            to=ta,
            scope=singleton,
        )

    FlaskInjector(app=app, modules=[module], )

    app.run('localhost', port=5001)

    thread = threading.Thread(target=start, args=())
    thread.daemon = True  # Daemonize thread
    thread.start()

