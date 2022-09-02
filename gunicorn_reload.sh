#!/usr/bin/env sh

gunicorn -b 0.0.0.0:8000 phc_bot.main:app --reload --log-file -
