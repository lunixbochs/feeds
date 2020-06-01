from flask import Flask, Response, abort, redirect, render_template, request
from flask_pymongo import PyMongo
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
mongo = PyMongo(app)

@app.before_first_request
def setup_indexes():
    indexes = {
        'feeds': [('numeric_id', 1)],
        'calls': [[('ts', -1), ('feed_id', 1)]],
    }
    for name, items in indexes.items():
        col = mongo.db[name]
        for index in items:
            kwargs = {}
            if not isinstance(index, list):
                index = [index]
            col.ensure_index(index, background=True, **kwargs)
