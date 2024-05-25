#!/bin/bash
CURRENT_DIR=`pwd`
set -e
cd $HOME
echo "[Build Mod] Cloning Repository"
git clone https://github.com/takpika/mcAIj.git > /dev/null
cd mcAIj
git checkout 1.19.2dev > /dev/null
echo "[Build Mod] Building Mod"
./gradlew build > /dev/null
cp build/libs/modid-1.0.jar ../aimod-1.0.jar
cd ..
rm -rf mcAIj
cd $CURRENT_DIR
echo "[Build Mod] Build Mod completed"