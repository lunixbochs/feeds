from speech_engines import gcpengine, w2lengine, nullengine
import audio_stream
import hashlib
import tempfile
import trunk_stream
import queue
import threading
import os

def tts_stream(queue, engine):
    while True:
        call = queue.get()
        if call.duration < 0.200:
            continue
        samples = call.audio_segment.get_array_of_samples()
        text = engine.decode(samples)
        if text:
            call.text = text
            yield call
        else:
            print('no text', call.duration)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', '-e', help='engine to use',  type=str, choices=('gcp', 'w2l', 'none'), default='w2l')
    parser.add_argument('--type',         help='stream type',    type=str, choices=('audio', 'trunk'), required=True)
    parser.add_argument('--w2l',          help='w2l data path',  type=str, default='w2l')
    parser.add_argument('--record',       help='recording path', type=str)
    parser.add_argument('stream',         help='system id or url', type=str)
    args = parser.parse_args()

    cookie = os.getenv('BCFY_COOKIE')
    if args.type == 'trunk' and not cookie:
        raise ValueError('missing cookie for trunk stream: set BCFY_COOKIE=...')

    if args.engine == 'w2l':
        engine = w2lengine(args.w2l)
    elif args.engine == 'gcp':
        engine = gcpengine()
    elif args.engine == 'none':
        engine = nullengine()
    else:
        raise RuntimeError('unknown engine {}'.format(args.engine))

    call_queue = queue.Queue()
    if args.type == 'trunk':
        call_system = trunk_stream.BroadcastifyCallSystem(args.stream, cookie, hydrate=60) # grab last 60s to fill buffer
        thread = threading.Thread(target=trunk_stream.scraper_thread, args=(call_system, call_queue))
        thread.start()
    elif args.type == 'audio':
        thread = threading.Thread(target=audio_stream.ffmpeg_thread, args=(args.stream, call_queue))
        thread.start()
    else:
        raise RuntimeError('unknown stream type: {}'.format(args.type))

    if args.record:
        os.makedirs(args.record, exist_ok=True)
    for call in tts_stream(call_queue, engine):
        if args.record:
            path = ''
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                path = f.name
                call.audio_segment.export(path, format='mp3', parameters=['-codec:a', 'libmp3lame', '-qscale:a','2'])
            with open(path, 'rb') as f:
                data = f.read()
                sha1 = hashlib.sha1(data).hexdigest()
            with open(os.path.join(args.record, sha1 + '.mp3'), 'wb') as f:
                f.write(data)
        print(call.ts, call.text)
