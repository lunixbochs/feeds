from flask import Response, request, abort
from datetime import datetime
import bson
import hmac
import json
import pymongo
import time

def _json_unknown(obj):
    if isinstance(obj, bson.ObjectId):
        return str(obj)
    elif isinstance(obj, pymongo.cursor.Cursor):
        return list(obj)
    elif isinstance(obj, datetime):
        return time.mktime(obj.timetuple())
    raise TypeError(type(object))

def json_encode(j):
    return json.dumps(j, default=_json_unknown)

def json_response(d, status=200):
    return Response(json_encode(d), mimetype='text/json', status=status)

def json_error(msg, status=400):
    return json_response({ 'error': msg }, status=status)

def require_auth():
    if not 'API_KEY' in app.config:
        app.logger.warn("API_KEY not set")
        abort(403)
    if not hmac.compare_digest(request.headers['authorization'], app.config['API_KEY']):
        abort(403)

def new_transcription(text, ts=None, source='user'):
    if ts is None:
        ts = datetime.utcnow()
    return ({
        '_id': bson.ObjectId(),
        'ts': ts,
        'text': text,
        'upvotes': 1 if source == 'user' else 0,
        'downvotes': 0,
        'source': source,
    })


from .app import app
