from bson import ObjectId
from datetime import datetime, timedelta, timezone
from flask import Response, abort, redirect, render_template, request
import json
import os
import pymongo

from .app import app, mongo
from .utils import json_error, json_response, new_transcription, require_auth

@app.route('/')
def slash():
    feeds = list(mongo.db.feeds.find())
    # TODO: aggregate, or store this on the feed when you insert a call, or something instead of doing N extra queries
    now = datetime.now(timezone.utc)
    for feed in feeds:
        newest_call = mongo.db.calls.find_one(
            {'feed_id': feed['_id']},
            projection=['ts'],
            sort=[('ts', pymongo.DESCENDING)])
        if newest_call:
            ts = feed['last_ts'] = newest_call['ts']
            feed['active'] = now - ts <= timedelta(days=0.5)
            feed['hours_ago'] = int((now - ts).total_seconds() / 60 / 60)
    feeds.sort(key=lambda x: x['name'])
    return render_template('index.html',
                           feeds=feeds,
                           time_now=now)

def _get_feed(feed_id, since=None, limit=200):
    query = {'feed_id': feed_id}
    if since is not None:
        query.update({
            '$or': [
                {'update_ts': {'$gte': since}},
                {'update_ts': {'$exists': False}, 'ts': {'$gte': since}},
            ],
        })
        query['update_ts'] = {'$gte': since}
    return mongo.db.calls.find(
        query,
        projection=['ts', 'audio_url', 'transcriptions._id', 'transcriptions.ts', 'transcriptions.text',
            'transcriptions.upvotes', 'transcriptions.downvotes', 'transcriptions.source'],
        limit=limit,
        sort=[('ts', pymongo.DESCENDING)]
    )

@app.route('/feeds/<ObjectId:feed_id>')
def get_feed(feed_id):
    feed = mongo.db.feeds.find_one_or_404({'_id': feed_id})
    calls = list(_get_feed(feed_id, limit=2000))
    for call in calls:
        call['transcriptions'].sort(key=lambda x: (x['upvotes'] - x['downvotes']), reverse=True)
    return render_template(
        'feed.html',
        feed=feed,
        feed_id=str(feed_id),
        last_timestamp=0,
        calls=calls,
        time_now=datetime.now(timezone.utc),
    )

@app.route('/api/feeds/<ObjectId:feed_id>')
def get_feed_text(feed_id):
    since = None
    if 'since' in request.args:
        since = datetime.utcfromtimestamp(float(request.args['since'])).replace(tzinfo=timezone.utc)
    limit = min(2000, int(request.args.get('limit', 2000)))
    calls = _get_feed(feed_id, since=since, limit=limit)
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
        'update_ts': datetime.fromisoformat(j['ts']),
        'audio_url': j['audio_url'],
        'audio_length': j['audio_length'],
        'from': j.get('from', None),
        'to': j.get('to', None),
        'transcriptions': [transcription]
    })
    return 'ok'

@app.route('/api/calls/<ObjectId:call_id>/transcribe', methods=['POST'])
def suggest(call_id):
    text = request.form.get('text', '')
    if len(text) < 3 or len(text) > 1000:
        return json_error('Invalid Text')

    ts = datetime.now(timezone.utc)
    call = mongo.db.calls.find_one_and_update(
        { '_id': call_id, 'transcriptions.text': {'$nin': [text]} },
        {
            '$push': { 'transcriptions': new_transcription(text, ts=ts, source='user') },
            '$set': { 'update_ts': ts },
        },
        return_document=pymongo.ReturnDocument.AFTER)
    if call is None:
        # TODO: this could also be call id not found, but we'll assume it's a dup for now
        return json_error("Duplicate transcription")
    else:
        return json_response(call)

@app.route('/api/transcriptions/<ObjectId:transcription_id>/vote', methods=['POST'])
def upvote(transcription_id):
    vote = int(request.form.get('vote', 0))
    if vote == 1:
        result = mongo.db.calls.find_one_and_update(
            { 'transcriptions._id': transcription_id },
            {
                '$inc': { 'transcriptions.$.upvotes': 1 },
                '$set': { 'update_ts': datetime.now(timezone.utc) },
            },
            return_document=pymongo.ReturnDocument.AFTER)
    elif vote == -1:
        result = mongo.db.calls.find_one_and_update(
            { 'transcriptions._id': transcription_id },
            {
                '$inc': { 'transcriptions.$.downvotes': 1 },
                '$set': { 'update_ts': datetime.now(timezone.utc) },
            },
            return_document=pymongo.ReturnDocument.AFTER)
    else:
        return json_error("Invalid Vote", status=400)
    if result is None:
        return json_error("Call not found", status=404)
    return json_response(result)
