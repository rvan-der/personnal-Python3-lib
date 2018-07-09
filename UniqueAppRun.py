from win32.win32api import *
from win32.win32file import *
from win32.win32process import *
from os import (path, mkdir, getenv, getpid, environ)


class AppNameError(Exception):
	def __init__(self, message):
		self.message = message


class OSFileSystemError(Exception):
	def __init__(self, message):
		self.message = message


class PidFileError(Exception):
	def __init__(self, message):
		self.message = message


class WinUniqueAppRun():
	def __init__(self, appName):
		self.appName = appName
		self.deletion = True
		self.nameError = False
		self.fileSysError = False
		self.pidFileError = None
		self.pidFileHandle = None
		self.appDataDir = ""
		self.pidFile = ""
		if not path.isdir(path.normpath(path.join("C:\\Users", getenv("USERNAME"), "AppData\\Local"))):
			self.fileSysError = True
		if self.appName == None or self.appName == "" or '\\' in self.appName:
			self.nameError = True
		else:
			self.appDataDir = path.normpath(path.join(environ['APPDATA'], appName))
			self.pidFile = path.normpath(path.join(self.appDataDir, appName + ".pid"))

	def __enter__(self):
		if self.nameError or self.fileSysError:
			return False
		if not path.isdir(self.appDataDir):
			mkdir(self.appDataDir)
		if path.isfile(self.pidFile) and self.IsValidPidFile():
			self.deletion = False
			return False
		if not self.CreatePidFile():
			self.deletion = True
			return False
		return True

	def __exit__(self, type, value, traceback):
		if self.pidFileHandle:
			self.pidFileHandle.close()
		if self.deletion:
			try:
				DeleteFile(self.pidFile)
			except:
				pass
		if self.fileSysError:
			raise OSFileSystemError("\"%s\" doesn't exist." % (path.dirname(self.appDataDir)))
		if self.nameError:
			raise AppNameError("Invalid app name. Empty or containing \'\\\'.")
		if self.pidFileError:
			raise PidFileError("Couldn't create \"%s\" (%s)" % (self.pidFile, str(self.pidFileError)))
		return False

	def CreatePidFile(self):
		try:
			pidFileHandle = CreateFile(self.pidFile,
										GENERIC_WRITE,
										0,
										None,
										CREATE_ALWAYS,
										FILE_ATTRIBUTE_NORMAL,
										None)
		except Exception as e:
			self.pidFileError = e
			return False
		WriteFile(pidFileHandle, str(getpid()).encode())
		pidFileHandle.close()
		self.pidFileHandle = CreateFile(self.pidFile,
								GENERIC_READ,
								FILE_SHARE_READ,
								None,
								OPEN_EXISTING,
								FILE_ATTRIBUTE_NORMAL,
								None)
		return True

	def IsValidPidFile(self):
		fileHandle = CreateFile(self.pidFile,
								GENERIC_READ,
								FILE_SHARE_READ,
								None,
								OPEN_EXISTING,
								FILE_ATTRIBUTE_NORMAL,
								None)
		read = ReadFile(fileHandle, 6)
		fileHandle.close()
		if read[0] != 0:
			return False
		try:
			filePid = int(read[1])
		except:
			return False
		if filePid in EnumProcesses():
			try:
				procHandle = OpenProcess(0x0410, False, filePid)
			except:
				return False
			moduleName = path.basename(path.normpath(GetModuleFileNameEx(procHandle, 0)))
			if self.appName in moduleName or "python" in moduleName:
				procHandle.close()
				return True
			procHandle.close()
		return False
