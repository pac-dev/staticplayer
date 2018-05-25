#!/usr/bin/env python

import sys, logging, staticplayer

if len(sys.argv)==1:
	print('Usage: python staticplayer-gen.py config_file.yml')
	sys.exit(0)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format="%(message)s")
sps = staticplayer.Site(configFilePath=sys.argv[1])
sps.generateSite()
