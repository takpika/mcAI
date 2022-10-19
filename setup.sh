#!/bin/bash
if [ ! -d mcAI ]; then
    git clone https://github.com/takpika/mcAI.git
else
    git pull https://github.com/takpika/mcAI.git
fi
cd mcAI
python install.py $@