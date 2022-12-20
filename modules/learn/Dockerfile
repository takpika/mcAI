FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo

RUN apt update
RUN apt install tzdata -y
RUN apt install git sudo -y
RUN useradd -m -d /var/mcai -s /bin/bash mcai
RUN echo "mcai ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
RUN cd /var/mcai && sudo -u mcai git clone https://github.com/takpika/mcAI.git
RUN cd /var/mcai/mcAI && sudo -u mcai git checkout development && sudo -u mcai git pull && sudo -u mcai bash modules/learn/setup.sh
RUN chown -R mcai:mcai /var/mcai/models

CMD ["/init"]