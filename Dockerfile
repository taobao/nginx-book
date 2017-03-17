
FROM ubuntu:14.04

MAINTAINER Taoge <wenter.wu@daocloud.io>

RUN apt-get update \
    && apt-get install -y software-properties-common \
    && apt-get install -y python-pip \
    && pip install pip --upgrade \
    && apt-add-repository -y ppa:nginx/stable \
    && apt-get update \
    && apt-get install -y nginx



RUN mkdir -p /usr/src/app

COPY ./requirements.txt /usr/src/app/

RUN pip install  -r /usr/src/app/requirements.txt

COPY . /usr/src/app

WORKDIR /usr/src/app

RUN make html
RUN cp /usr/src/app/nginx_base.conf /etc/nginx/nginx.conf
RUN cp /usr/src/app/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx","-g","daemon off;"]
