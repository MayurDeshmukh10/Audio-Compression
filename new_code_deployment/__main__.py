from scipy.io.wavfile import write
from scipy.io import wavfile
from sklearn.decomposition import PCA
import numpy as np
import pydub
import sys
import base64
import os
import ibm_boto3
from ibm_botocore.client import Config, ClientError

COS_ENDPOINT = "#" 
COS_API_KEY_ID_DOWNLOAD = "#" 
COS_API_KEY_ID_UPLOAD = "#"
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_RESOURCE_CRN_DOWNLOAD = "#"
COS_RESOURCE_CRN_UPLOAD = "#"


def pca_reduce(signal, n_components, block_size=1024):
    
    	# First, zero-pad the signal so that it is divisible by the block_size
	samples = len(signal)
	hanging = block_size - np.mod(samples, block_size)
	padded = np.lib.pad(signal, (0, hanging), 'constant', constant_values=0)
    
    	# Reshape the signal to have 1024 dimensions
	reshaped = padded.reshape((len(padded) // block_size, block_size))
    
    			# Second, do the actual PCA process
	pca = PCA(n_components=n_components)
	pca.fit(reshaped)
    
	transformed = pca.transform(reshaped)
	reconstructed = pca.inverse_transform(transformed).reshape((len(padded)))
	return pca, transformed, reconstructed


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


	samplerate, tabulasa = wavfile.read('inputfile.wav')

	start = samplerate * 14 # 10 seconds in
	end = start + samplerate * 10 # 5 second duration

	tabulasa_left = tabulasa[:,0]
    
	_, _, reconstructed = pca_reduce(tabulasa_left, 64, 256)

	scaled = np.int16(reconstructed/np.max(np.abs(reconstructed)) * 32767)
	write('compressed.wav', 44100, scaled)

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
