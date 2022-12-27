FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo

RUN apt update
RUN apt install tzdata -y
RUN apt install git sudo -y
RUN apt install libcudnn8 libcudnn8-dev -y
RUN useradd -m -d /var/mcai -s /bin/bash mcai
RUN echo "mcai ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
RUN cd /var/mcai && sudo -u mcai git clone https://github.com/takpika/mcAI.git
RUN cd /var/mcai/mcAI && sudo -u mcai git pull && sudo -u mcai bash modules/learn/setup.sh

CMD ["/init"]