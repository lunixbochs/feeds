from flask import Response, request, abort
from datetime import datetime
import bson
import hmac
import json
import pymongo
import sys
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

def json_response(d):
    return Response(json_encode(d), mimetype='text/json')

def require_auth():
    if not 'API_KEY' in app.config:
        sys.stderr.write("API_KEY not set\n")
        abort(403)
    if not hmac.compare_digest(request.form['key'], app.config['API_KEY']):
        abort(403)

from .app import app
