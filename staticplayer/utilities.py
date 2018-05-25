import os, shutil, distutils.spawn

memoizedCommands = {}
def getVerifiedCommand(cmd, givenPath = None):
	if cmd not in memoizedCommands:
		if givenPath is None:
			ret = distutils.spawn.find_executable(cmd)
			if ret is None:
				raise IOError("Required command not found: "+cmd)
		else:
			if not os.path.exists(givenPath):
				raise IOError("Required command not found at the path provided in the config file:\n"+givenPath)
			ret = givenPath
		memoizedCommands[cmd] = ret
	return memoizedCommands[cmd]

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
