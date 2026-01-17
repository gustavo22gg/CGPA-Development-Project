#!/usr/bin/env bash
# exit on error
set -o errexit

STORAGE_DIR=/opt/render/project/.render

echo "...Downloading Chrome"
mkdir -p $STORAGE_DIR/chrome
cd $STORAGE_DIR/chrome
# Download the stable Chrome binary
wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
# Unpack it (no root required)
dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
rm ./google-chrome-stable_current_amd64.deb
cd $HOME/project/src # Return to source directory

# Install Python dependencies
pip install -r requirements.txt
