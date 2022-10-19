#!/bin/bash
sudo hostnamectl set-hostname $1
if [ -e /etc/hostname ]; then
    CURRENT_HOSTNAME=`cat /etc/hostname`
    sudo sed -i -e "s/$CURRENT_HOSTNAME/$1/g" /etc/hosts
fi