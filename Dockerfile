FROM python:3.8

WORKDIR /GLCheckerUser

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt -U

COPY . .