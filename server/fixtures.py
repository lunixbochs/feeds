from bson import ObjectId
from datetime import datetime
import random

chicago_text = '''
67-55 or at North World Walgreens we got a boost we got looters in custody
all right hand for the looters and cosplay at the Walgreens at North Avenue or Wells of Learners across super 67-65
what do you want from the first district sir
one of the arresting officers 662 team 662 team
172 is asking for one of the officers to come to one regarding the president's going to area for
breaking a window
okay okay 131 unsuited Ten-Four
says looters accosted a Walgreens at North Avenue and Wells
get to it because these Chillicothe is our 18th District wagon for North Avenue alzate District wagon
progress Central trying to drop offers either any other wagon of Alvord abdominal Wells
714 boy 6714 box
seven to go at Federal and west
all right 171 did I hear you out about 171
once you guys should come to push this year except the one that they want to take to all
'''.strip().split('\n')

sfpd_text = '''
want more
number of the place before it's going to be
I don't want to seven
you can put me on that 418 verbal at 901 Clemente
regarding 1014 Vermont for men
glass is still glass windows still intact but all shattered
and I'm coming in the district as a family unit
and the baby you five and a party for five nine one zero nine five fingers in process will continue
number 7
John 11 everything
for a 4/5 1980 penthouse
nice to having destination at Google market and Valley
side by side
32 expired on a nice on how to surf
overall review that are run in the white
that's whatever
'''.strip().split('\n')

feeds = [
    {
        '_id': ObjectId(),
        'source': 'broadcastify',
        'name': 'Chicago Police',
        'shortname': 'chicago-pd',
        'tags': ['chicago', 'police'],
        'url': 'http://example.com',
        'numeric_id': 1223,
    },
    {
        '_id': ObjectId(),
        'source': 'broadcastify',
        'name': 'SFPD',
        'shortname': 'sfpd',
        'tags': ['san francisco', 'police'],
        'url': 'http://example.com',
        'numeric_id': 1224,
    },
]
chicago_id = feeds[0]['_id']
sfpd_id = feeds[1]['_id']

def make_call(feed_id, text):
    return {
        '_id': ObjectId(),
        'feed_id': feed_id,
        'ts': datetime.utcnow(),
        'audio_url': 'https://example.com/TODO.mp3',
        'audio_length': random.random() * 10,
        'from': str(random.randint(1000, 9999)),
        'to':   str(random.randint(1000, 9999)),
        'transcriptions': [
            {
                '_id': ObjectId(),
                'ts': datetime.utcnow(),
                'text': text,
                'upvotes': random.randint(0, 3),
                'downvotes': random.randint(0, 3),
                'source': 'google',
            },
            {
                '_id': ObjectId(),
                'ts': datetime.utcnow(),
                'text': text.lower(),
                'upvotes': random.randint(0, 3),
                'downvotes': random.randint(0, 3),
                'source': 'user',
            },
        ],
    }

calls = []
for line in chicago_text:
    calls.append(make_call(chicago_id, line))

for line in sfpd_text:
    calls.append(make_call(sfpd_id, line))

if __name__ == '__main__':
    from pymongo import MongoClient
    client = MongoClient()
    db = client.feeds

    db.feeds.drop()
    db.calls.drop()

    for feed in feeds:
        db.feeds.insert_one(feed)
    for call in calls:
        db.calls.insert_one(call)
