
from pydub import AudioSegment

import matplotlib.pyplot as plt
import numpy as np
import wave
import sys
import math
import contextlib
from pylab import*
from scipy.io import wavfile
import pyaudio

fname = 'tt.wav'
outname = 'test_compressed.wav'


cutOffFrequency = 20000



def run_mean(x, windowSize):
  cumsum = np.cumsum(np.insert(x, 0, 0)) 
  return (cumsum[windowSize:] - cumsum[:-windowSize]) / windowSize


def interpret_wav(raw_bytes, n_frames, n_channels, sample_width, interleaved = True):

    if sample_width == 1:
        dtype = np.uint8 # unsigned char
    elif sample_width == 2:
        dtype = np.int16 # signed 2-byte short
    else:
        raise ValueError("Only supports 8 and 16 bit audio formats.")

    channels = np.fromstring(raw_bytes, dtype=dtype)
    if interleaved:
        # channels are interleaved, i.e. sample N of channel M follows sample N of channel M-1 in raw data
        channels.shape = (n_frames, n_channels)
        channels = channels.T
    else:
        # channels are not interleaved. All samples from channel M occur before all samples from channel M-1
        channels.shape = (n_channels, n_frames)

    return channels

#song = AudioSegment.from_mp3("1mb.mp3")
#song.export("final.wav", format="wav")


with contextlib.closing(wave.open(fname,'rb')) as spf:
    sampleRate = spf.getframerate()
    ampWidth = spf.getsampwidth()
    nChannels = spf.getnchannels()
    nFrames = spf.getnframes()

    # Extract Raw Audio from multi-channel Wav File
    signal = spf.readframes(nFrames*nChannels)
    spf.close()
    channels = interpret_wav(signal, nFrames, nChannels, ampWidth, True)

    # get window size
    fqRatio = (cutOffFrequency/sampleRate)
    N = int(math.sqrt(0.196196 + fqRatio**2)/fqRatio)

    # Use moviung average (only on first channel)
    filt = run_mean(channels[0], N).astype(channels.dtype)

    wav_file = wave.open(outname, "w")
    wav_file.setparams((1, ampWidth, sampleRate, nFrames, spf.getcomptype(), spf.getcompname()))
    wav_file.writeframes(filt.tobytes('C'))
    wav_file.close()


#sound = AudioSegment.from_wav("final.wav")
#sound.export("apple.mp3", format="mp3")   
    
'''n = 0
for n in range (0,2): 
    if n==0:
        fft_dis(fname)
    elif n==1:
        fft_dis(outname)'''
