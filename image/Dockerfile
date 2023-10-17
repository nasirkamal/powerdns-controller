FROM python:3.11.6-alpine3.18
WORKDIR /

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./* .
RUN chmod +x main.py
CMD /main.py