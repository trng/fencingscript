#!/bin/bash

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
FILE_NAME="fencingApparatus.service"
FULL_FILE_NAME="$SCRIPT_DIR/$FILE_NAME"
FULL_SERVICE_NAME="/etc/systemd/system/$FILE_NAME"

ln -s "$FULL_FILE_NAME" "$FULL_SERVICE_NAME"
systemctl daemon-reload
systemctl enable $FILE_NAME
systemctl stop $FILE_NAME
systemctl start $FILE_NAME