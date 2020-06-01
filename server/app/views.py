from datetime import datetime
from flask import Response, abort, redirect, render_template, request
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
import json
import os
import pymongo

from .app import app, mongo
from .utils import json_response, new_transcription, require_auth

class ExampleForm(FlaskForm):
    text = StringField('text', validators=[DataRequired()])

@app.route('/')
def slash():
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
        projection=['ts','transcriptions._id','transcriptions.ts','transcriptions.text',
            'transcriptions.upvotes','transcriptions.downvotes','transcriptions.source'],
        limit=200,
        sort=[('ts', pymongo.DESCENDING)]
    )

@app.route('/feeds/<ObjectId:feed_id>')
def get_feed(feed_id):
    calls = _get_feed(feed_id)
    return render_template(
        'feed.html',
        feed_id=str(feed_id),
        last_timestamp=0,
        calls=calls,
    )

@app.route('/api/feeds/<ObjectId:feed_id>')
def get_feed_text(feed_id):
    calls = _get_feed(feed_id)
    return json_response(calls)

@app.route('/api/calls', methods=['POST'])
def add_call():
    require_auth()
    j = request.json
    if 'feed_id' in j:
        feed = mongo.db.feeds.find_one_or_404({'_id': ObjectId(j['feed_id'])})
    elif 'feed_num' in j:
        feed = mongo.db.feeds.find_one_or_404({'numeric_id': j['feed_num']})
    else:
        abort(500)

    transcription = new_transcription(j['text'],
                                      ts=datetime.fromisoformat(j['text_ts']),
                                      source=j['text_source'])
    mongo.db.calls.insert_one({
        'feed_id': feed['_id'],
        'ts': datetime.fromisoformat(j['ts']),
        'audio_url': j['audio_url'],
        'audio_length': j['audio_length'],
        'from': j.get('from', None),
        'to': j.get('to', None),
        'transcriptions': [transcription]
    })
    return 'ok'

@app.route('/suggest/<ObjectId:call_id>', methods=['POST'])
def suggest(call_id):
    text = request.form.get('text', '')
    if len(text) < 3 or len(text) > 1000:
        return json_response({ 'success': False, 'reason': 'Invalid Text' })

    print(new_transcription(text))

    result = mongo.db.calls.update_one(
        {'_id': call_id},
        { '$push': { 'transcriptions': new_transcription(text, source='user') } }
    )
    if result.modified_count == 1:
        return json_response({ 'success': True })
    else:
        abort(404)

@app.route('/upvote/<ObjectId:transcription_id>', methods=['POST'])
def upvote(transcription_id):
    result = mongo.db.calls.update_one(
        { 'transcriptions._id': transcription_id },
        { '$inc': { 'transcriptions.$.upvotes': 1 } }
    )
    if result.modified_count == 1:
        return json_response({ 'success': True })
    else:
        abort(404)

@app.route('/downvote/<ObjectId:transcription_id>', methods=['POST'])
def downvote(transcription_id):
    result = mongo.db.calls.update_one(
        { 'transcriptions._id': transcription_id },
        { '$inc': { 'transcriptions.$.downvotes': 1 } }
    )
    if result.modified_count == 1:
        return json_response({ 'success': True })
    else:
        abort(404)
