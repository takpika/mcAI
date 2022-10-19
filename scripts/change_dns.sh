#!/bin/bash
DNS_SERVER=`cat /etc/resolv.conf | grep nameserver | awk '{print $2}'`
sudo sed -i -e "s/$DNS_SERVER/$1/g" /etc/resolv.conf