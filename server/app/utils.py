from flask import Response
from datetime import datetime
import bson
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

def json_response(d):
    return Response(json_encode(d), mimetype='text/json')

def require_auth():
    if not hmac.compare_digest(request.form['key'], app.config[SECRET_KEY]):
        abort(403)

from .app import app
