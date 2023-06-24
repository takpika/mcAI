FROM ubuntu:latest

ARG BRANCH
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt update > /dev/null
RUN apt install tzdata -y > /dev/null
RUN apt install git sudo -y > /dev/null
RUN useradd -m -d /var/mcai -s /bin/bash mcai > /dev/null
RUN echo "mcai ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
RUN echo "Defaults always_set_home" >> /etc/sudoers
RUN cd /var/mcai && sudo -u mcai git clone https://github.com/takpika/mcAI.git > /dev/null
RUN cd /var/mcai/mcAI && sudo -u mcai git checkout ${BRANCH} && sudo -u mcai git pull && sudo -u mcai -E bash modules/learn/setup.sh

CMD ["/init"]