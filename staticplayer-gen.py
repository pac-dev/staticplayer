#!/usr/bin/env python

import sys, staticplayer

if len(sys.argv)==1:
	print('Usage: python staticplayer-gen.py config_file.yml')
	sys.exit(0)

sps = staticplayer.PlaylistSite(configFilePath=sys.argv[1])
sps.generateAll()
sps.copyAudioFiles()
sps.reportVBR()
