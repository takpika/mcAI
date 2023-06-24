FROM ubuntu:latest

ARG BRANCH
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV FLAVOR=local

RUN apt update > /dev/null
RUN apt install tzdata -y > /dev/null
RUN apt install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" keyboard-configuration > /dev/null
RUN apt install git sudo -y > /dev/null
RUN useradd -m -d /var/mcai -s /bin/bash mcai > /dev/null
RUN echo "mcai ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
RUN echo "Defaults always_set_home" >> /etc/sudoers
ADD --chown=mcai:mcai ./ /var/mcai/mcAI/
RUN cd /var/mcai/mcAI && sudo -u mcai -E bash modules/client/setup.sh

CMD ["/init"]