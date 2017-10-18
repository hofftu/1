#!/usr/bin/env python3
import sys
import os
import classes.config

if len(sys.argv) < 2:
    print('usage: convert.py <old_wanted> (relative paths only for now)')
    exit()

conf = classes.config.Config(os.path.join(sys.path[0], 'config.conf'))
with open(os.path.join(sys.path[0], sys.argv[1])) as source:
    for id in (int(line) for line in source.readlines()):
        if id not in conf.filter.wanted.dict.keys():
            conf.filter.wanted.set_data(id)
