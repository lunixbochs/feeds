from dataclasses import dataclass
from datetime import datetime
import array
import atexit
import ffmpeg
import os
import pydub
import struct
import subprocess
import sys
import threading
import time
import traceback
import typing
import wave
import webrtcvad

@dataclass
class Call:
    # these four properties shared with trunk_stream.Call
    ts: datetime
    duration: float
    audio_segment: pydub.AudioSegment
    text: str

def poll_thread(p):
    while True:
        if p.poll() is not None:
            break
        time.sleep(1)

def stream(url, verbose=False):
    while True:
        cmd = ffmpeg.input(url).output('-', format='s16le', acodec='pcm_s16le', ac=1, ar='16k').compile()
        with open(os.devnull, 'w+') as devnul:
            p = subprocess.Popen(cmd, stdin=devnul, stdout=subprocess.PIPE, stderr=devnul)

        # need to poll so subprocess will get cleaned up
        thread = threading.Thread(target=poll_thread, args=(p,), daemon=True)
        thread.start()

        def kill():
            p.kill()
            p.stdout.close()
        atexit.register(kill)
        vad = webrtcvad.Vad(0)
        chunks = []
        try:
            while True:
                chunk = p.stdout.read(480 * 2)
                if not chunk:
                    break
                if vad.is_speech(chunk, 16000):
                    chunks.append(chunk)
                elif chunks:
                    yield b''.join(chunks)
                    chunks = []
        except Exception:
            pass
        print('[!] Stream disconnected, sleeping...', file=sys.stderr)
        time.sleep(1)

def ffmpeg_thread(url, q):
    for raw_speech in stream(url):
        ts = datetime.utcnow()
        samples = array.array('h', raw_speech)
        segment = (pydub.AudioSegment.empty()
                   .set_sample_width(2)
                   .set_channels(1)
                   .set_frame_rate(16000))
        audio_segment = segment._spawn(samples)
        duration = len(samples) / 16000
        call = Call(ts=ts, audio_segment=audio_segment, duration=duration, text='')
        q.put(call)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', '-e', help='engine to use',  type=str, choices=('gcp', 'w2l'), default='w2l')
    parser.add_argument('--w2l',          help='w2l data path',  type=str, default='w2l')
    parser.add_argument('--record',       help='recording path', type=str)
    parser.add_argument('url',            help='stream url',     type=str)
    args = parser.parse_args()

    record_n = 0
    if args.record:
        os.makedirs(args.record, exist_ok=True)
        for name in os.listdir(args.record):
            try:
                record_n = max(record_n, int(name.split('.', 1)[0]))
            except Exception:
                pass

    if args.engine == 'w2l':
        engine = w2lengine(args.w2l)
    elif args.engine == 'gcp':
        engine = gcpengine()
    else:
        raise RuntimeError('unknown engine {}'.format(args.engine))
    for date, text, samples in tts_stream(args.url, engine):
        if text.count(' ') >= 1:
            if args.record:
                with wave.open(os.path.join(args.record, '{}.wav'.format(record_n)), 'wb') as w:
                    binary = struct.pack('<{}h'.format(len(samples)), *samples)
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(16000)
                    w.writeframes(binary)
                with open(os.path.join(args.record, '{}.txt'.format(record_n)), 'w') as f:
                    f.write(text + '\n')
                record_n += 1
            ts = date.strftime('%Y/%m/%d %H:%M:%S.%f UTC')
            sys.stdout.write('{}] {}\n'.format(ts, text))
            sys.stdout.flush()
