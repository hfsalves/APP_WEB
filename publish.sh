#!/bin/bash
git add .
if [ -z "$1" ]
then
    git commit -m "$(date '+%Y-%m-%d %H:%M')"
else
    git commit -m "$1"
fi
git push
