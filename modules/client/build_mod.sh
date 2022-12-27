#!/bin/bash
CURRENT_DIR=`pwd`
cd ~/
git clone https://github.com/takpika/mcAIj.git
cd mcAIj
git checkout 1.19.2dev
./gradlew build
cp build/libs/modid-1.0.jar ../aimod-1.0.jar
cd ..
rm -rf mcAIj
cd $CURRENT_DIR