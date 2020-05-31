import wav2letter
import struct

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
