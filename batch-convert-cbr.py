#!/usr/bin/env python

import os, sys, subprocess

if len(sys.argv)==1:
	print('Usage:  python batch-convert-cbr.py file_list.txt')
	sys.exit(0)

f = open(sys.argv[1], "r")
for sourcePath in f:
	print((sourcePath.rstrip()))
sys.stdout.write("\nWARNING: This script will overwrite all the above media files"
	+ " with 192k CBR mp3 versions (probably lower-quality)."
	+ "\n\nAre you sure you want to continue? (enter yes to continue, anything else to abort)\n>")
choice = input().lower()
if choice not in ('yes','y', 'ye'):
	sys.exit("Aborted by user.")

f.seek(0)
for sourcePath in [l.rstrip() for l in f]:
	if not os.path.exists(sourcePath):
		sys.exit("error: file does not exist: " + sourcePath)
	sourceDir, sourceBaseName = os.path.split(sourcePath)
	tempPath = sourceDir + "/TEMP_CBR_" + sourceBaseName
	print(("Re-encoding " + sourceBaseName))
	p = subprocess.Popen(
		['ffmpeg.exe', 
		'-nostdin', 
		'-i', sourcePath, 
		'-b:a', '192k', 
		'-id3v2_version', '3',
		tempPath],
		stdout=subprocess.PIPE, 
		stderr=subprocess.PIPE
	)
	out, err = p.communicate()
	if p.returncode != 0:
		print("Re-encoding failed. The output of the command was:")
		print((out + "\n" + err))
		sys.exit("error: Re-encoding failed for " + sourcePath)
	os.remove(sourcePath)
	os.rename(tempPath, sourcePath)
print("All files converted successfully! What crime has been committed!?")
