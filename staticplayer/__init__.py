#!/usr/bin/env python
"""Static Online Playlist Generator."""

import sys, os, shutil, codecs, json, jinja2, yaml, __main__
from mutagen import mp3, easyid3
try:
	from urllib.parse import quote
except ImportError:
	from urllib import quote
if os.name != "nt":
	import ntpath
	
		
def recursiveOverwrite(src, dest, ignore=None):
	copiedFiles = []
	if os.path.isdir(src):
		if not os.path.isdir(dest):
			os.makedirs(dest)
		files = os.listdir(src)
		ignored = set() if ignore is None else ignore(src, files)
		for f in [f for f in files if f not in ignored]:
			copiedFiles += recursiveOverwrite(
				os.path.join(src, f), 
				os.path.join(dest, f), 
				ignore
			)
	else:
		shutil.copyfile(src, dest)
		return [dest]
	return copiedFiles
	
def removeEmptyDirs(root):
	for dirpath, _, _ in os.walk(root, topdown=False):
		if dirpath == root:
			break
		try:
			os.rmdir(dirpath)
		except OSError as ex:
			pass # not empty


class PlaylistSite:
	def __init__(self, configFilePath='staticplayer.yml'):
		self.configFilePath = os.path.realpath(configFilePath)
		self.parseConfig() # todo config parser error
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
		self.newFilesInOutput = {"webFiles":[], "audioFiles":[]}
		self.analyzedFiles = []
		self.oldValidFiles = []
		for pl in self.configData["playlists"]:
			pl["tracks"] = self.expandPlaylistFiles(pl["tracks"]) # todo playlist parser error
			pl["tracks"] = [self.inspectAudioFile(tr,pl) for tr in pl["tracks"]] # todo audio file analysis error
			if not self.configData["multiPlaylist"]: break
	
	def ymlPath2AbsPath(self, path):
		if os.path.isabs(path):
			return path
		else:
			return os.path.join(os.path.dirname(self.configFilePath), path)
	
	def prepareInputPath(self, path):
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
		self.configData = yaml.load(configFile)
		configFile.close()
		self.outPath = self.ymlPath2AbsPath(self.configData["outputPath"])
		if "copyAudioTo" in self.configData:
			self.audioOutPath = self.ymlPath2AbsPath(self.configData["copyAudioTo"])
		
	def withChRoot(self, playlistPath, trackPath):
		for chRoot in self.configData["inputPlaylistChRoots"]:
			chRoot = os.path.join(os.path.realpath(chRoot), '')
			playlistPath = os.path.realpath(playlistPath)
			if os.path.commonprefix([playlistPath, chRoot]) == chRoot:
				return os.path.normpath(chRoot + os.path.splitdrive(trackPath)[1])
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
					line = self.withChRoot(entry, line)
				else:
					line = os.path.normpath(os.path.join(playlistDirectory, line))
				newTracks.append(line)
		return newTracks
	
	def inspectAudioFile(self, filePath, list=None):
		id3 = easyid3.EasyID3(filePath)
		mp3data = mp3.MP3(filePath)
		title = id3["title"][0] if "title" in id3 else os.path.splitext(os.path.basename(filePath))[0]
		artist = id3["artist"][0] if "artist" in id3 else "?"
		album = id3["album"][0] if "album" in id3 else "?"
		subdir = list["shortName"]+"/" if list is not None else ""
		self.analyzedFiles.append({
			"path": filePath,
			"targetPath": "" if self.audioOutPath is None else self.audioOutPath + subdir + os.path.basename(filePath),
			"isVBR": mp3data.info.bitrate_mode in (mp3.BitrateMode.VBR, mp3.BitrateMode.ABR),
		})
		return {
			"filename": os.path.basename(filePath),
			"url": self.configData["publicAudioPath"] 
			+ subdir + quote(os.path.basename(filePath).encode("utf-8")),
			"title": title,
			"artist": artist,
			"album": album,
			"length": "%d:%02d" % divmod(mp3data.info.length, 60),
		}
	
	def cleanupOutputDir(self):
		# delete previous website files
		for f in self.oldFilesInOutput["webFiles"]:
			if os.path.exists(f):
				os.remove(f)
		# delete outdated audio files
		oldAudioFiles = [file for file in self.oldFilesInOutput["audioFiles"] if os.path.exists(file)]
		for oldFile in oldAudioFiles:
			if os.path.normpath(oldFile) in [os.path.normpath(file["targetPath"]) for file in self.analyzedFiles]:
				self.oldValidFiles.append(oldFile)
			else:
				os.remove(oldFile)
		removeEmptyDirs(self.audioOutPath)
		removeEmptyDirs(self.outPath)
	
	def generateSite(self):
		self.cleanupOutputDir()
		self.generatePages()
		self.copyAudioFiles()
		# turn absolute paths into relative from yml so we can write them to file_list
		relNewFiles = {
			key:[os.path.relpath(file, os.path.dirname(self.configFilePath)) for file in files]
				for key,files in self.newFilesInOutput.items()
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
		self.newFilesInOutput["webFiles"] += copiedFiles
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
		self.newFilesInOutput["webFiles"].append(listOutPath+'index.html')
		
	def copyAudioFiles(self):
		if self.audioOutPath is None: return
		for fileInfo in self.analyzedFiles:
			src = fileInfo["path"]
			dst = fileInfo["targetPath"]
			fileInfo["path"] = dst
			if dst in self.oldValidFiles:
				continue
			if not os.path.exists(os.path.dirname(dst)):
				os.makedirs(os.path.dirname(dst))
			if not os.path.exists(dst):
				shutil.copyfile(src, dst)
			self.newFilesInOutput["audioFiles"].append(dst)
	
	def reportVBR(self):
		vbrs = [f["path"] for f in self.analyzedFiles if f["isVBR"]]
		nvbr = len(vbrs)
		if nvbr > 0:
			print(("\nWarning: detected %d VBR mp3s. They will have a buggy seek bar in Firefox. Use batch-convert-cbr.py to convert them." % nvbr))
			print ("Following is the list of VBR files:")
			print(('\n'.join([f for idx,f in enumerate(vbrs) if idx < 5])))
			if nvbr > 5:
				vbrFile = open ("vbr_list.txt", "w")
				[vbrFile.write(f+os.linesep) for f in vbrs]
				print ("...\nList too long. Full list written to vbr_list.txt")
		
		