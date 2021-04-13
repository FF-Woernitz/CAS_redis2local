FROM python:3-alpine

RUN apk add --no-cache git gcc libc-dev python3-dev

WORKDIR /opt/redis2local
COPY requirements.txt ./

ADD "https://api.github.com/repos/FF-Woernitz/CAS_lib/git/refs/heads/master" skipcache
RUN CFLAGS="-fcommon" pip install --no-cache-dir -r requirements.txt

RUN apk del --no-cache git gcc libc-dev python3-dev

COPY src .

CMD [ "python3", "-u", "./main.py" ]
