import os, shutil, subprocess, logging
from .utilities import *

log = logging.getLogger(__name__)

class AudioJob():
	def __init__(self, src, dst, transcode):
		self.src = src
		self.dst = dst
		self.transcode = transcode
		self.currentPath = src
	
	def run(self):
		if os.path.exists(self.dst):
			log.warning("Output file already exists: "+self.dst)
		if not os.path.exists(os.path.dirname(self.dst)):
			os.makedirs(os.path.dirname(self.dst))
		if self.transcode:
			self.runTranscode()
		else:
			self.runCopy()
		self.currentPath = self.dst
		return self.dst
	
	def runCopy(self):
		if not os.path.exists(self.dst):
			shutil.copyfile(self.src, self.dst)
	
	def runTranscode(self):
		log.debug("Transcoding file: "+self.src)
		p = subprocess.Popen(
			[getVerifiedCommand("ffmpeg"),
			'-nostdin',
			'-y',
			'-i', self.src,
			'-b:a', self.transcode,
			'-id3v2_version', '3',
			self.dst],
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
		)
		out, err = p.communicate()
		if p.returncode != 0:
			raise IOError("Transcoding failed for the following input file:\n"+
			self.src+"\nThe output of the command was:\n" + out + "\n" + err)
