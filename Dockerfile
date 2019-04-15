FROM alpine:3.7

RUN apk add --no-cache \
        tzdata \
        python3 \
        py3-pip \
        py3-pillow \
        py3-numpy \
        py3-yaml \
        py3-requests \
    && pip3 install pytelegraf


COPY libs /libs

COPY run.py /run.py
COPY logging.ini /logging.ini

VOLUME /persist

CMD ["python3", "run.py", "/config.yml"]
