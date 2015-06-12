#!/bin/bash

# change here to match local machine folder structure
local_folder=$HOME/data/PanoFallback/ARB-GV-HILL-1/
remote_mounted_folder=$HOME/data/gigavision/ARB-GV-HILL-1/
log_folder=$HOME/data/gigavision/log/

# copy new files
rsync -av --progress --log-file=$log_folder/$(date +%Y%m%d)_upload.log $local_folder $remote_mounted_folder

# remove local folder 7 days before
year=$(date -d "-7 days" +%Y)
month=$(date -d "-7 days" +%m)
day=$(date -d "-7 days" +%d)
old_local_folder=$local_folder/$year/$year"_"$month/$year"_"$month"_"$day
if [ -d "$old_local_folder" ]; then
  rm -rf $old_local_folder
fi
