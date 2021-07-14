FROM python:3.8.10-buster

# TODO

ADD . /app/co2_env_measurement
WORKDIR /app/co2_env_measurement

RUN pip install -r requirements.txt

CMD python main.py