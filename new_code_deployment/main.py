import pydub
import numpy as np
import wave
import sys
import math
import contextlib
from scipy.io import wavfile
import pyaudio
import ibm_boto3
from ibm_botocore.client import Config, ClientError

COS_ENDPOINT = "#" 
COS_API_KEY_ID_DOWNLOAD = "#" 
COS_API_KEY_ID_UPLOAD = "#"
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_RESOURCE_CRN_DOWNLOAD = "#"
COS_RESOURCE_CRN_UPLOAD = "#"

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


def main(args):
	audio = args['__ow_body']
	headers = args["__ow_headers"]
	audio_extension = headers['content_type']

	unique_filename = audio.split('=')[1]

	print("Unique Filename : ",unique_filename)

	cos_download = ibm_boto3.resource("s3",
        ibm_api_key_id=COS_API_KEY_ID_DOWNLOAD,
        ibm_service_instance_id=COS_RESOURCE_CRN_DOWNLOAD,
        ibm_auth_endpoint=COS_AUTH_ENDPOINT,
        config=Config(signature_version="oauth"),
        endpoint_url=COS_ENDPOINT)

	try:
		file = cos_download.Object("imagecompressionuploads",unique_filename).get()
	except ClientError as be:
		print("CLIENT ERROR: {0}\n".format(be))
		return { 'statusCode': 400, 'body': be } 
	except Exception as e1:
		print("Unable to retrieve file contents: {0}".format(e1))
		return { 'statusCode': 400, 'body': e1 }

	audio_data = file["Body"].read()

	if audio_extension == 'mp3':
		with open('input.mp3','wb') as f:
			f.write(audio_data)
		sound = pydub.AudioSegment.from_mp3("input.mp3")
		sound.export("inputfile.wav", format="wav")
		
	else:
		with open('inputfile.wav','wb') as f:
			f.write(audio_data)

	

	with contextlib.closing(wave.open('inputfile.wav','rb')) as spf:
	    print("TYPE : ",type(spf))
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

	    wav_file = wave.open("compressed.wav", "w")
	    wav_file.setparams((1, ampWidth, sampleRate, nFrames, spf.getcomptype(), spf.getcompname()))
	    wav_file.writeframes(filt.tobytes('C'))
	    wav_file.close()

	if audio_extension == 'mp3':
		sound1 = pydub.AudioSegment.from_wav("compressed.wav")
		sound1.export("compressed.mp3", format="mp3")

	try:
		cos_upload = ibm_boto3.resource("s3",ibm_api_key_id=COS_API_KEY_ID_UPLOAD,ibm_service_instance_id=COS_RESOURCE_CRN_UPLOAD,ibm_auth_endpoint=COS_AUTH_ENDPOINT,config=Config(signature_version="oauth"),endpoint_url=COS_ENDPOINT)
		print("Starting file transfer for {0} to bucket: {1}\n".format(unique_filename, "imagecompressiondownloads"))
		part_size = 1024 * 1024 * 5
		file_threshold = 1024 * 1024 * 40
		transfer_config = ibm_boto3.s3.transfer.TransferConfig(
		    multipart_threshold=file_threshold,
		    multipart_chunksize=part_size
		)
		if audio_extension == 'mp3':
			with open("compressed.mp3", "rb") as file_data:
		    		cos_upload.Object("imagecompressiondownloads", unique_filename).upload_fileobj(
		        		Fileobj=file_data,
		        		Config=transfer_config
		    		)
		else:
			with open("compressed.wav", "rb") as file_data:
		    		cos_upload.Object("imagecompressiondownloads", unique_filename).upload_fileobj(
		        			Fileobj=file_data,
		        			Config=transfer_config
		    			)
		print("Transfer for {0} Complete!\n".format(unique_filename))

	except ClientError as be:
		print("CLIENT ERROR: {0}\n".format(be))
		return { 'statusCode': 400, 'body': be }
	except Exception as e:
		print("Unable to complete multi-part upload: {0}".format(e))
		return { 'statusCode': 400, 'body': e }

	return { 'statusCode': 200, 'body': "Compression Successfully" } 
			 

	 
