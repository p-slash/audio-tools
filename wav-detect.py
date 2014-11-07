#!/usr/bin/env python

import collections
import numpy
import pyaudio
import sys
import time
import wave

from numpy.fft import rfft, irfft

WIDTH = 2
CHANNELS = 1
RATE = 44100
CHUNK = 1024
ID_FREQS = 6 # number of identifier freqs
THRESHOLD = 10 ** -80

IS_PLAYING = False
DTYPE = None
MAX_LEVEL = None


def import_wav_file (filename):
    wf = wave.open(filename, "rb")

    if wf.getsampwidth() != WIDTH or wf.getnchannels() != CHANNELS or wf.getframerate() != RATE:
        return False
        
    wav_sample = []
    
    data = wf.readframes(CHUNK)
    while data != '':
        id_freqs_of_block = find_max_freqs(data)
        if id_freqs_of_block != None:
            wav_sample.append( id_freqs_of_block )
        
        data = wf.readframes(CHUNK)
        
    AudioQueue.init(wav_sample)
    return True


def start_recording ():
    p = pyaudio.PyAudio()

    stream = p.open(format=p.get_format_from_width(WIDTH),
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=callback)

    stream.start_stream()
    
    num_diff_status = 0
    last_status = AudioQueue.is_playing
    print last_status
    
    while stream.is_active():
        if AudioQueue.is_playing != last_status:
            num_diff_status += 1
            
            if num_diff_status > 10: # equivalent to 1 second
                last_status = not last_status
                print last_status
        
        else:
            num_diff_status = 0
        
        time.sleep(0.1)

    stream.stop_stream()
    stream.close()

    p.terminate()


def callback (in_data, frame_count, time_info, status):
    AudioQueue.add(find_max_freqs(in_data))
    
    AudioQueue.check_queue()
    
    return (None, pyaudio.paContinue)
    
    
def find_max_freqs (data):
    data = numpy.fromstring(data, dtype=DTYPE)
    
    if len(data) != CHUNK:
        return None
        
    dft = (1.0 / MAX_LEVEL) * abs( rfft(data) )
    
    sorted_index = numpy.argsort(dft)[::-1]
    
    return sorted_index[:ID_FREQS]
    
    
def get_numpy_dtype (width):
    if width == 1:
        return numpy.int8
    elif width == 2:
        return numpy.int16
    elif width == 4:
        return numpy.int32
    
    return None


class AudioQueue (object):
    @classmethod
    def init (cls, sample):
        cls.is_playing = False
        cls.sample = sample
        cls.maxlen = len(sample)
        cls.queue = collections.deque(maxlen=cls.maxlen)
        
    @classmethod
    def add (cls, max_freqs):
        cls.queue.append(max_freqs)
        
    @classmethod
    def check_queue (cls):
        if len(cls.queue) < cls.maxlen:
            return False
            
        prob = 1.0
        
        for i in range(cls.maxlen):
            equal = 0
            min_queue_samp = min(len(cls.queue[i]), len(cls.sample[i]))
            
            for f1 in cls.queue[i]:
                f1prev = f1 - 1
                f1next = f1 + 1
                if f1 in cls.sample[i] or f1prev in cls.sample[i] or f1next in cls.sample[i]:
                    equal += 1
            
            prob *= float(1 + equal) / (1 + min_queue_samp)
            
        #print prob
        
        if prob > THRESHOLD:
            cls.is_playing = True
            return True
            
        else:
            cls.is_playing = False
            return False


if __name__ == '__main__':
    DTYPE = get_numpy_dtype(WIDTH)
    MAX_LEVEL = 2 ** (8 * WIDTH - 1)
    
    if DTYPE == None:
        print "Unknown DTYPE."
        sys.exit(-1)
    
    if len(sys.argv) < 2:
        print "No wave file is given. Usage: %s wavefile.wav" % sys.argv[0]
        sys.exit(-1)
        
    if not import_wav_file(sys.argv[1]):
        print "Given wave file properties are different than expected values."
        sys.exit(-1)
    
    start_recording()
