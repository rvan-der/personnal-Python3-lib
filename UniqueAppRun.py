#Author Rémy Van der Zijden
#Usage:
#This class must be used as a context manager, it works only on Windows.
#It creates a pid file that serves to identify the first launched process of the module/program.
#The whole execution of the module/program needs to be encapsulated because the pid file is deleted
#when exiting the context manager. So if that happens before end of execution, it won't work.
#The app name must correspond to the name of the module or executable file in order to correctly identify the process.
#Examples:
#1. if you want your program to be launched only once:
#	myAppName = __file__
#	with WinFirstAppRun(myAppName) as first:
#		if first:
#			myApp()
#
#2. if you want certain instructions to be executed only at first launch:
#	myAppName = __file__
#	with WinFirstAppRun(myAppName) as first:
#		myApp(first)
#
#	def myApp(first):
#		if first:
#			print("only executed at first launch")
#		print("always executed")

from win32.win32api import *
from win32.win32file import *
from win32.win32process import *
from os import (path, mkdir, getenv, getpid, environ)


class AppNameError(Exception):
	def __init__(self, message):
		self.message = message


class PidFileError(Exception):
	def __init__(self, message):
		self.message = message


class WinFirstAppRun():
	def __init__(self, appName):
		if not appName or '\\' in self.appName:
			raise AppNameError("Invalid app name. Empty or containing \'\\\'.")
		self.appName = appName
		self.first = True
		self.pidFileHandle = None
		self.appDataDir = path.normpath(path.join(environ['APPDATA'], appName))
		self.pidFile = path.normpath(path.join(self.appDataDir, appName + ".pid"))

	def __enter__(self):
		#create appDataDir if it doesn't exist
		if not path.isdir(self.appDataDir):
			mkdir(self.appDataDir)
		#check if there already exists a pid file
		if path.isfile(self.pidFile):
			#if it is valid return False meaning there is already an instance running
			if self.IsValidPidFile():
				self.first = False #for knowing if cleaning needs to be done at __exit__
				return False
			#if it isn't valid try to delete it and raise exception if impossible
			try:
				DeleteFile(self.pidFile)
			except Exception as e:
				raise PidFileError("An invalid pid file named \"%s\" already exists. Couldn't delete it: %s" % (self.pidFile, str(e)))
		#create pid file and return True meaning there was no instance already running
		self.CreatePidFile():
		return True

	def __exit__(self, type, value, traceback):
		if self.first:
			self.pidFileHandle.close()
			DeleteFile(self.pidFile)
		return False

	def CreatePidFile(self):
		#Open pidFile for creation with write permission
		try:
			pidFileHandle = CreateFile(self.pidFile,
										GENERIC_WRITE,
										0,
										None,
										CREATE_ALWAYS,
										FILE_ATTRIBUTE_NORMAL,
										None)
		except Exception as e:
			raise PidFileError("Couldn't create \"%s\". (%s)" % (self.pidFile, str(e)))
		#Write pid of current process to the file
		WriteFile(pidFileHandle, str(getpid()).encode())
		pidFileHandle.close()
		#Reopen the pid file with read-only permission so user and other programs can't write to it
		self.pidFileHandle = CreateFile(self.pidFile,
								GENERIC_READ,
								FILE_SHARE_READ,
								None,
								OPEN_EXISTING,
								FILE_ATTRIBUTE_NORMAL,
								None)

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
			if self.appName.lower() in moduleName.lower() or "python" in moduleName:
				procHandle.close()
				return True
			procHandle.close()
		return False
