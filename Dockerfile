FROM ubuntu:18.04

RUN apt-get update -y

RUN apt-get install locales -y
RUN locale-gen en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8

RUN pip3 install --upgrade pip

ADD ./requirements.txt /tmp/requirements.txt

RUN pip3 install -r /tmp/requirements.txt