from broadcastify import BroadcastifyCallSystem, Call
from speech_engines import w2lengine, gcpengine
from pydub import AudioSegment
from io import BytesIO
import queue
import threading
import requests
import hashlib
import os
from timeit import default_timer as timer

def scraper_thread(call_system, call_queue, record_path):
    for call in call_system.calls():
        # get the call audio
        r = requests.get(call.audio_uri)
        r.raise_for_status() # TODO: warn?

        audio = AudioSegment.from_file(BytesIO(r.content), format=call.encoding)

        start = timer()
        m = hashlib.sha1()
        m.update(audio.raw_data)
        audio_id = m.hexdigest()

        call_queue.put((call, audio_id, audio))

        if args.record:
            export_path = os.path.join(args.record, '{}.mp3'.format(audio_id))
            if call.encoding == 'mp3':
                with open(export_path, 'wb') as f:
                    f.write(r.content)
            else:
                start = timer()
                audio.export(export_path, format='mp3', parameters=['-codec:a','libmp3lame', '-qscale:a','2'])
                end = timer()
                print('[.] reencoded ({} -> mp3), δt = {:.2}s'.format(call.encoding, end-start))

            # audio.export(, format='wav')

def tts_stream(queue, engine):
    while True:
        call, audio_id, int16_samples = queue.get()
        text = engine.decode(int16_samples)
        if text:
            yield (call, audio_id, text)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', '-e', help='engine to use',  type=str, choices=('gcp', 'w2l', 'none'), default='w2l')
    parser.add_argument('--w2l',          help='w2l data path',  type=str, default='w2l')
    parser.add_argument('--record',       help='recording path', type=str)
    parser.add_argument('--auth',         help='broadcastify auth cookie', type=str, required=True)
    parser.add_argument('id',             help='system id',     type=str)
    args = parser.parse_args()

    if args.engine == 'w2l':
        engine = w2lengine(args.w2l)
    elif args.engine == 'gcp':
        engine = gcpengine()
    elif args.engine == 'none':
        class fakeengine:
            def __init__(self):
                pass
            def decode(self, samples):
                return 'test string'
        engine = fakeengine()
    else:
        raise RuntimeError('unknown engine {}'.format(args.engine))

    if args.record:
        os.makedirs(args.record, exist_ok=True)

    call_system = BroadcastifyCallSystem(args.id, args.auth, hydrate=60) # grab last 60s to fill buffer
    
    call_queue = queue.Queue()
    scraper_thread = threading.Thread(target=scraper_thread,
                                      args=(call_system, call_queue, args.record))
    scraper_thread.start()

    for call, audio_id, text in tts_stream(call_queue, engine):
        print(call, text)