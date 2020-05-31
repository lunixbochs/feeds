from datetime import datetime
import atexit
import ffmpeg
import os
import queue
import struct
import subprocess
import sys
import threading
import time
import traceback
import wav2letter
import wave
import webrtcvad

class w2lengine:
    def __init__(self, path=None):
        if path is None:
            path = os.path.join(os.path.dirname(__file__), 'w2l')
        w2l_loader = wav2letter.W2lLoader(path)
        self.model = w2l_loader.load()

    def decode(self, samples):
        float_samples = [s / 32768 for s in samples]
        emit, decode = self.model.decode(float_samples)
        return decode

class gcpengine:
    def __init__(self):
        from google.cloud import speech_v1
        from google.cloud.speech_v1 import enums
        self.client = speech_v1.SpeechClient()
        self.config = {
            'model': 'video',
            'language_code': 'en-US',
            'sample_rate_hertz': 16000,
            'encoding': enums.RecognitionConfig.AudioEncoding.LINEAR16,
        }

    def decode(self, samples):
        binary = struct.pack('<{}h'.format(len(samples)), *samples)
        audio = {'content': binary}
        response = self.client.recognize(self.config, audio)
        for result in response.results:
            alternative = result.alternatives[0]
            return alternative.transcript

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
        date = datetime.utcnow()
        count = len(raw_speech) // 2
        fmt = '<{}h'.format(count)
        int16_samples = struct.unpack(fmt, raw_speech)
        q.put((date, int16_samples))

def tts_stream(url, engine):
    audio_queue = queue.Queue()
    thread = threading.Thread(target=ffmpeg_thread, args=(url, audio_queue))
    thread.start()

    while True:
        date, int16_samples = audio_queue.get()
        text = engine.decode(int16_samples)
        if text:
            yield (date, text, int16_samples)

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
