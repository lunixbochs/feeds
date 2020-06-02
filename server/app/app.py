from flask import Flask, Response, abort, redirect, render_template, request
from flask_pymongo import PyMongo
import hashlib
import json
import os
import pymongo

app = Flask('feeds')
app.config.update({
    'MONGO_URI': 'mongodb://localhost:27017/feeds',
    'SECRET_KEY': os.urandom(16).hex(),
})
if 'FLASK_SETTINGS' in os.environ:
    app.config.from_envvar('FLASK_SETTINGS')
mongo = PyMongo(app, tz_aware=True)

_static_cache = {}
@app.template_filter('cachebust')
def cachebust(filename):
    sha1 = _static_cache.get(filename)
    if sha1: return sha1
    path = os.path.join(app.static_folder, filename)
    with open(path, 'rb') as f:
        sha1 = hashlib.sha1(f.read()).hexdigest()
    busted = filename + '?' + sha1
    _static_cache[filename] = busted
    return busted

@app.before_first_request
def setup_indexes():
    indexes = {
        'feeds': [('numeric_id', 1)],
        'calls': [
            ('feed_id', 1),
            [('ts', -1), ('feed_id', 1)],
        ],
    }
    for name, items in indexes.items():
        col = mongo.db[name]
        for index in items:
            kwargs = {}
            if not isinstance(index, list):
                index = [index]
            col.ensure_index(index, background=True, **kwargs)
