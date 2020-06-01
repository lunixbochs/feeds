from flask import Response, abort, redirect, render_template, request
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
import hmac
import json
import os
import pymongo

from .app import app, mongo
from .utils import json_response, require_auth

class ExampleForm(FlaskForm):
    text = StringField('text', validators=[DataRequired()])

@app.route('/')
def slash():
    print('slash')
    obj = {'text': '', 'votes': 0}
    vote_obj = mongo.db.votes.find_one({'post_id': 1})
    if vote_obj: obj = vote_obj
    form = ExampleForm()
    form.text.data = obj['text']
    return render_template('index.html', obj=obj, form=form)

@app.route('/feeds')
def feed_index():
    feeds = mongo.db.feeds.find()
    return render_template('feed_index.html', feeds=feeds)

def _get_feed(feed_id):
    mongo.db.feeds.find_one_or_404({'_id': feed_id})
    return mongo.db.calls.find(
        {'feed_id': feed_id},
        projection=['ts','transcriptions'],
        limit=200,
        sort=[('ts', pymongo.DESCENDING)]
    )

@app.route('/feeds/<ObjectId:feed_id>')
def get_feed(feed_id):
    calls = _get_feed(feed_id)
    return render_template('feed.html', feed_id=feed_id, calls=calls)

@app.route('/api/feeds/<ObjectId:feed_id>', methods=['GET','POST'])
def get_feed_text(feed_id):
    if request.method == 'GET':
        calls = _get_feed(feed_id)
        return json_response(calls)
    elif request.method == 'POST':
        require_auth()

        feed = mongo.db.feeds.find_one_or_404({'_id': feed_id})
        #mongod.db.calls.insertMany( TKTK )

        # TODO
        return 'ok'

@app.route('/upvote', methods=['POST'])
def upvote():
    form = ExampleForm()
    if form.validate_on_submit():
        mongo.db.votes.find_one_and_update({'post_id': 1},
                                           {'$inc': {'votes': 1}, '$set': {'text': form.text.data}}, new=True, upsert=True)
    return redirect('/', code=302)

@app.route('/downvote', methods=['POST'])
def downvote():
    form = ExampleForm()
    if form.validate_on_submit():
        mongo.db.votes.find_one_and_update({'post_id': 1},
                                           {'$inc': {'votes': 1}, '$set': {'text': form.text.data}}, new=True, upsert=True)
    return redirect('/', code=302)
