import sys, os, __main__, codecs, logging, json, jinja2, yaml, mutagen
#from mutagen import mp3, easyid3
try:
	from urllib.parse import quote
except ImportError:
	from urllib import quote
if os.name != "nt":
	import ntpath

from .audiojob import AudioJob
from .utilities import *

log = logging.getLogger(__name__)

class Site:
	def __init__(self, configFilePath='staticplayer.yml'):
		self.configFilePath = os.path.realpath(configFilePath)
		self.configData = self.parseConfig()
		getVerifiedCommand("ffmpeg", self.prepareInputPath(self.configData.get("ffmpegPath")))
		self.listFileName = os.path.splitext(configFilePath)[0] + ".file_list"
		try:
			with open(self.listFileName, 'r') as listFile:
				self.oldFilesInOutput = json.load(listFile)
		except IOError as err:
			# file_list does not exist yet
			self.oldFilesInOutput = {"webFiles":[], "audioFiles":[]}
		except:
			# json parsing failed
			print("skipping broken file list")
			self.oldFilesInOutput = {"webFiles":[], "audioFiles":[]}
		# file_list should contain relative paths from yml, make them absolute
		self.oldFilesInOutput = {
			key:[self.ymlPath2AbsPath(file) for file in files]
				for key,files in self.oldFilesInOutput.items()
		}
		self.validFilesInOutput = {"webFiles":[], "audioFiles":[]}
		self.audioJobs = []
		for pl in self.configData["playlists"]:
			pl["tracks"] = self.expandPlaylistFiles(pl["tracks"])
			pl["tracks"] = [self.inspectAudioFile(tr,pl) for tr in pl["tracks"]]
			if not self.configData["multiPlaylist"]: break
	
	def ymlPath2AbsPath(self, path):
		if os.path.isabs(path):
			return path
		else:
			return os.path.join(os.path.dirname(self.configFilePath), path)
	
	def prepareInputPath(self, path):
		if path is None: return None
		newPath = path
		errorPaths = []
		if not os.path.isabs(path):
			newPath = self.ymlPath2AbsPath(path)
			if not os.path.exists(newPath):
				errorPaths.append(newPath)
				newPath = os.path.join(os.path.dirname(__main__.__file__), path)
		if not os.path.exists(newPath):
			errorPaths.append(newPath)
			raise IOError("Input file not found: "+
				os.path.basename(path)+
				"\nAttempted the following paths:\n"+
				"\n".join(errorPaths)
			)
		return newPath
	
	def parseConfig(self):
		configFile = open(self.configFilePath)
		configData = yaml.load(configFile)
		configFile.close()
		self.outPath = self.ymlPath2AbsPath(configData["outputPath"])
		if "copyAudioTo" in configData:
			self.audioOutPath = self.ymlPath2AbsPath(configData["copyAudioTo"])
		return configData
		
	def withMountpoint(self, playlistPath, trackPath):
		for mountpoint in self.configData["inputPlaylistMountpoints"]:
			mountpoint = os.path.join(os.path.realpath(mountpoint), '')
			playlistPath = os.path.realpath(playlistPath)
			if os.path.commonprefix([playlistPath, mountpoint]) == mountpoint:
				return os.path.normpath(mountpoint + os.path.splitdrive(trackPath)[1])
		return trackPath
	
	def expandPlaylistFiles(self, tracks):
		newTracks = []
		for entry in tracks:
			ext = os.path.splitext(entry)[1]
			if ext == ".m3u":
				encoding = "ascii"
			elif ext == ".m3u8":
				encoding = "utf-8-sig"
			else:
				newTracks.append(self.prepareInputPath(entry))
				continue
			entry = self.prepareInputPath(entry)
			playlistDirectory = os.path.dirname(entry)
			with codecs.open(entry, "r", encoding) as f:
				playlistLines = [l for l in f if not l.startswith('#EXTINF')]
			joined = "".join(playlistLines)
			win2posix = os.name != "nt" and "\\" in joined and "/" not in joined
			if win2posix: 
				print((os.path.basename(entry) + " paths contain only back slashes. Assuming Windows paths."))
			for line in playlistLines:
				line = line.rstrip()
				if win2posix:
					if ntpath.isabs(line):
						line = ntpath.splitdrive(line)[1]
					line = line.replace('\\', '/')
				if os.name == "nt" and os.path.isabs(line):
					line = os.path.normpath(line)
					if (line[0]=='\\'):
						line = os.path.splitdrive(playlistDirectory)[0]+line
				if os.path.isabs(line):
					line = self.withMountpoint(entry, line)
				else:
					line = os.path.normpath(os.path.join(playlistDirectory, line))
				newTracks.append(line)
		return newTracks
	
	def inspectAudioFile(self, filePath, list=None):
		mfile = mutagen.File(filePath, easy=True)
		splitext = os.path.splitext(os.path.basename(filePath))
		if splitext[1]=="mp3":
			shouldTranscode = mp3.MP3(filePath).info.bitrate_mode in (mp3.BitrateMode.VBR, mp3.BitrateMode.ABR)
		else:
			shouldTranscode = True
		title = mfile.get("title") or splitext[0]
		artist = mfile.get("artist") or "?"
		album = mfile.get("album") or "?"
		subdir = list["shortName"]+"/" if list is not None else ""
		self.audioJobs.append(AudioJob(
			src = filePath,
			dst = "" if self.audioOutPath is None else self.audioOutPath + subdir + os.path.basename(filePath),
			transcode = self.configData["bitrate"] if shouldTranscode else False
		))
		return {
			"filename": os.path.basename(filePath),
			"url": self.configData["publicAudioPath"] 
			+ subdir + quote(os.path.basename(filePath).encode("utf-8")),
			"title": title,
			"artist": artist,
			"album": album,
			"length": "%d:%02d" % divmod(mfile.info.length, 60),
		}
	
	def prepareOutputDir(self):
		# delete previous website files
		for f in self.oldFilesInOutput["webFiles"]:
			if os.path.exists(f):
				os.remove(f)
		# delete outdated audio files
		oldAudioFiles = [os.path.normpath(file) for file in self.oldFilesInOutput["audioFiles"] if os.path.exists(file)]
		for oldFile in oldAudioFiles:
			if oldFile in [os.path.normpath(file.dst) for file in self.audioJobs]:
				self.validFilesInOutput["audioFiles"].append(oldFile)
			else:
				os.remove(oldFile)
		removeEmptyDirs(self.audioOutPath)
		removeEmptyDirs(self.outPath)
	
	def generateSite(self):
		self.prepareOutputDir()
		self.generatePages()
		self.runAudioJobs()
		# turn absolute paths into relative from yml so we can write them to file_list
		relNewFiles = {
			key:[os.path.relpath(file, os.path.dirname(self.configFilePath)) for file in files]
				for key,files in self.validFilesInOutput.items()
		}
		with open(self.listFileName, 'w') as listFile:
			json.dump(relNewFiles, listFile, indent=1)
		print("Site ("+self.configData["pageTitle"]+") successfully generated to "+self.outPath)
	
	def generatePages(self):
		templateDir = self.prepareInputPath(self.configData["template"])
		copiedFiles = recursiveOverwrite(
			templateDir,
			self.outPath,
			ignore = lambda dir, list: [f for f in list if f.endswith(".jinja")]
		)
		self.validFilesInOutput["webFiles"] += copiedFiles
		if self.configData["multiPlaylist"]:
			# make index.html in root:
			self.generatePage(templateDir)
			# make playlist subdirectories and their index.html:
			for pl in self.configData["playlists"]:
				self.generatePage(templateDir, pl)
		else:
			self.generatePage(templateDir, self.configData["playlists"][0])
		
	def generatePage(self, templateDir, playlist=None):
		templateData = self.configData.copy()
		if playlist is not None:
			templateData.update(playlist)
		if "showPlaylistList" not in templateData:
			templateData["showPlaylistList"] = len(templateData["playlists"]) > 1 or playlist is None
		listOutPath = self.outPath
		if playlist is not None and self.configData["multiPlaylist"]:
			listOutPath += templateData["shortName"] + "/"
		if not os.path.exists(listOutPath):
			os.makedirs(listOutPath)
		templateEnv = jinja2.Environment(loader = jinja2.FileSystemLoader(templateDir))
		# load the template specified by the config yaml:
		
		template = templateEnv.get_template("index.jinja")
		index = codecs.open(listOutPath + 'index.html', 'w+', "utf-8")
		index.write(template.render(templateData))
		index.close()
		self.validFilesInOutput["webFiles"].append(listOutPath+'index.html')
		
	def runAudioJobs(self):
		if self.audioOutPath is None: return
		oldValidFiles = self.validFilesInOutput["audioFiles"]
		self.validFilesInOutput["audioFiles"] += [
			job.run() for job in self.audioJobs if job.dst not in oldValidFiles
		]
		skipped = len([job for job in self.audioJobs if job.dst in oldValidFiles])
		if skipped > 0:
			log.debug("Skipped {} audio files already in output.".format(skipped))
