FROM ubuntu:latest

RUN apt update
RUN apt install git sudo -y
RUN useradd -m -d /var/mcai -s /bin/bash mcai
RUN echo "mcai ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
RUN cd /var/mcai && sudo -u mcai git clone https://github.com/takpika/mcAI.git
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo
RUN cd /var/mcai/mcAI && sudo -u mcai git checkout development && sudo -u mcai git pull && sudo -u mcai bash modules/client/setup.sh

CMD ["/init"]