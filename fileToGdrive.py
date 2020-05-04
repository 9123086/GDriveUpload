"""
test @ 20200501
system environments
GDRIVE_SECRET_PATH point to the client secret file
TMP_SECRET_PATH point to the local secret token cache
"""


import os
import sys, traceback
import platform
from time import time, ctime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pickle 
import fnmatch
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logger = logging.getLogger( __name__ )


def saveIntoCache(cachedFile, dataToCache):
  outfile = open(cachedFile,'wb')
  pickle.dump(dataToCache,outfile)
  outfile.close()


def readFromCache(cachedFile):
  dataFromCache = None
  try:
    infile = open(cachedFile,'rb')
    dataFromCache = pickle.load(infile)
    infile.close()
  except:
    logger.error("exception when read cached file")

  return dataFromCache


def getNewFileList(pathToFolder, fileNamePattern):
  #get last check time stamp
  cachedDataFileName = "cachedDataFile.bin"
  cachedData = readFromCache(cachedDataFileName)
  if(cachedData is None):
    #save current time to cache
    cachedData = {"lastCheckTime": time.time()}
    saveIntoCache(cachedDataFileName, cachedData)

  #go through files in current directory
  newFileList = []
  listOfFiles = os.listdir(pathToFolder)

  for item in listOfFiles:
    itemEncoded = item.decode('iso-8859-1').encode("utf-8")

    if fnmatch.fnmatch(itemEncoded, fileNamePattern):
      newFileList.append({
        "name": itemEncoded, 
        "fileSavedTime": getFileTimeStamp(itemEncoded), 
        "lastCheckTime":cachedData["lastCheckTime"]})

  return newFileList


def getFileTimeStamp(pathToFile):
  
  if platform.system() == 'Windows':
      return os.path.getctime(pathToFile)
  else:
    try:
      stat = os.stat(pathToFile)
      return stat.st_birthtime
    except AttributeError:
        return stat.st_mtime
    except:
        return 0


def getGDrive(clientSecretPath):
  tmpCredsPath =  os.getenv("TMP_SECRET_PATH") 
  if( tmpCredsPath is None ):
    tmpCredsPath = "gdrive_secrets.bin"

  gauth = GoogleAuth()
  gauth.LoadClientConfigFile(clientSecretPath)

  #try to load saved client credetials
  gauth.LoadCredentialsFile(tmpCredsPath)
  if gauth.credentials is None:

    gauth.GetFlow()
    gauth.flow.params.update({'access_type': 'offline'})
    gauth.flow.params.update({'approval_prompt': 'force'})
     
    gauth.LocalWebserverAuth() 
  elif gauth.access_token_expired:
    gauth.Refresh()
  else:
    gauth.Authorize()

  drive = GoogleDrive(gauth)
  gauth.SaveCredentialsFile(tmpCredsPath)

  return drive


def uploadFile(gDrive, localFilePath, destFileId):
  # Initialize GoogleDriveFile instance with file id.
  file1 = gDrive.CreateFile({"mimeType": "text/csv", "parents": [{"kind": "drive#fileLink", "id": destFileId}]})
  file1.SetContentFile(localFilePath)

  try:
    file1.Upload()
    logger.info('Created file %s with mimeType %s' % (file1['title'], file1['mimeType']))
  except Exception as e:
    logger.error("upload exception: ")
    ex_type, ex, tb = sys.exc_info()
    traceback.print_tb(tb)


def getIdByTitle_InFolder(gDrive, folderId, title):

  qString = "'" + folderId + "' in parents and trashed=false"
  fileList = gDrive.ListFile({'q': qString}).GetList()
  fileID = ""
  for file in fileList:
    #logger.info('Title: %s, ID: %s' % (file['title'], file['id']))
    
    if(file['title'] == title):
        fileID = file['id']
  return fileID

def deleteFile(gDrive, targetFileId):
  # Initialize GoogleDriveFile instance with file id.
  file2 = gDrive.CreateFile({'id': targetFileId})
  file2.Trash()  # Move file to trash.
  file2.UnTrash()  # Move file out of trash.
  file2.Delete()  # Permanently delete the file.

########### main
def main():

  toShareFolder = "To Share"
  localFileName = "test.txt"

  clientSecret = os.getenv("GDRIVE_SECRET_PATH")
  if( clientSecret is None ): clientSecret = "mysecret.json"
  gDrive = getGDrive( clientSecret )
  folderId = getIdByTitle_InFolder(gDrive, 'root', toShareFolder) 
  fileId = getIdByTitle_InFolder(gDrive, folderId, localFileName)

  if(fileId is None or fileId == ""):
    uploadFile(gDrive, localFileName, folderId)
    logger.info("file: %s uploaded" % (localFileName))
  else:
    deleteFile(gDrive, fileId)
    logger.info("file: %s deleted" % (localFileName))

if __name__ == '__main__':
    main()
