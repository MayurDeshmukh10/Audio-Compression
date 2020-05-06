FROM openwhisk/python3aiaction

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
        python3-pip \
        gcc \
        libc-dev \
        libxslt-dev \
        libxml2-dev \
        libffi-dev \
        libssl-dev \
        libasound-dev \
        portaudio19-dev \
	ffmpeg \
        python3-pyaudio \
	libsox-fmt-mp3 \
        zip \
        unzip \
        libsm6 \
        libxrender1 \
        libfontconfig1 \
        vim \
        && rm -rf /var/lib/apt/lists/*



RUN apt-cache search linux-headers-generic

RUN apt-get update
RUN apt-get upgrade

RUN pip3 install --upgrade pip


RUN pip3 install \
    numpy \
    pydub \
    PyAudio \ 
    scipy \
    sklearn \
    ibm-cos-sdk==2.0.1 


RUN apt-get upgrade






