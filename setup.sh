#!/bin/bash
set -e
git clone https://github.com/takpika/mcAI.git
cd mcAI
python install.py $@