from dataclasses import dataclass, field
from datetime import datetime
import io
import json
import logging
import math
import pydub
import random
import requests
import time

ENDPOINT = 'https://www.broadcastify.com/calls/apis/livecall.php'
TAGS = {
    1: 'Multi-Dispatch',
    2: 'Law Dispatch',
    3: 'Fire Dispatch',
    4: 'EMS Dispatch',
    6: 'Multi-Tac',
    7: 'Law Tac',
    8: 'Fire-Tac',
    9: 'EMS-Tac',
    11: 'Interop',
    12: 'Hospital',
    13: 'Ham',
    14: 'Public Works',
    15: 'Aircraft',
    16: 'Federal',
    17: 'Business',
    20: 'Railroad',
    21: 'Other',
    22: 'Multi-Talk',
    23: 'Law Talk',
    24: 'Fire-Talk',
    25: 'EMS-Talk',
    26: 'Transportation',
    29: 'Emergency Ops',
    30: 'Military',
    31: 'Media',
    32: 'Schools',
    33: 'Security',
    34: 'Utilities',
    35: 'Data',
    36: 'Deprecated',
    37: 'Corrections'
}

@dataclass
class Call:
    # these four properties shared with audio_stream.Call
    ts: datetime
    duration: float
    audio_segment: pydub.AudioSegment
    text: str

    fileid: str
    encoding: str

    system: int
    tag: str
    talkgroup: int
    call_src: int

    display: str
    grouping: str
    description: str
    freq: float
    json: dict = field(repr=False)

    @property
    def audio_uri(self):
        return f"https://calls.broadcastify.com/{self.system}/{self.fileid}.{self.encoding}"

    @classmethod
    def from_json(cls, call):
        return cls(ts=datetime.fromtimestamp(int(call['ts'])),
            fileid=call['filename'],
            encoding=call['enc'],
            system=call['systemId'],

            tag=TAGS[int(call['tag'])],
            talkgroup=int(call['call_tg']),
            call_src=int(call['call_src']),

            display=call['display'],
            grouping=call['grouping'],
            description=call['descr'],

            duration=float(call['call_duration']),
            freq=float(call['tag']),
            audio_segment=None,
            text='',

            json=call)

class BroadcastifyCallSystem:
    def __init__(self, system_id, auth_cookie, hydrate=300):
        self.session_key = self._gen_session_key()
        self.system_id = system_id
        self.auth_cookie = auth_cookie
        self.init_request = True

        self.after_timestamp = math.floor(datetime.now().timestamp())-hydrate

    def calls(self):
        while True:
            start = time.monotonic()
            try:
                for call in self._poll():
                    yield Call.from_json(call)
            except Exception:
                logging.exception('failed to fetch calls')
            remain = 5 - (time.monotonic() - start)
            if remain > 0.1:
                time.sleep(remain)

    def _poll(self):
        resp = self._request(self.after_timestamp, self.init_request)
        if 'lastPos' in resp:
            self.after_timestamp = int(resp['lastPos'])
        self.init_request = False

        return resp['calls']

    def _request(self, after_timestamp, do_init):
        r = requests.post(ENDPOINT,
            data={
                'pos': after_timestamp,
                'doInit': do_init,
                'systemId': self.system_id,
                'sessionKey': self.session_key,
            },
            cookies={'bcfyuser1': self.auth_cookie})

        return r.json()

    @staticmethod
    def _gen_session_key():
        key = ''
        for _ in range(8):
            key += '{:x}'.format(random.getrandbits(4))
        key += '-'
        for _ in range(4):
            key += '{:x}'.format((random.getrandbits(4) & 0x3) | 0x8)

        return key

def scraper_thread(call_system, call_queue):
    for call in call_system.calls():
        try:
            r = requests.get(call.audio_uri)
            r.raise_for_status()
            audio = (pydub.AudioSegment.from_file(io.BytesIO(r.content), format=call.encoding)
                     .set_sample_width(2)
                     .set_channels(1)
                     .set_frame_rate(16000))
            call.audio_segment = audio
            call.duration = audio.duration_seconds
            call_queue.put(call)
        except Exception:
            logging.exception('failed to download: {}'.format(call.audio_uri))
