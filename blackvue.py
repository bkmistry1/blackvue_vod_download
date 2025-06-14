import os
import requests
import shutil
import asyncio
import subprocess
import aiohttp

from dotenv import load_dotenv

load_dotenv()

ip = os.getenv("blackvueIP")
downloadFolder = os.getenv("downloadFolder")
tmpFolder= os.getenv("tmpFolder")
print(ip, flush=True)

class videoFileClass(object):
    def __init__(self, fileName, source, destination):

        self.fileName = fileName
        self.source = source
        self.destination = destination

videoFileTransferList: list[videoFileClass] = []

async def newName(fileString: str):
    newName = fileString.replace("/Record/", "")
    newName = newName.replace(".mp4", "")
    return newName

async def checkAvailableSpace(path):
    # Run df command and process output
    result = subprocess.run(["df", path], capture_output=True, text=True)
    lines = result.stdout.split("\n")
    data = lines[1].split()

    # Calculate percentage available
    used_percentage = int(data[4].replace("%", ""))
    available_percentage = 100 - used_percentage

    return available_percentage

async def getFileList():
    fileList = []

    url = ip + "/blackvue_vod.cgi"

    response = None
    while(response == None or response.status_code != 200):
        print("checking", flush=True)
        try:
            response = requests.get(url=url, timeout=10)
        except Exception as e:
            print(e, flush=True)
        print("sleeping", flush=True)
        await asyncio.sleep(10)
    responseText = response.text

    responseText = responseText.replace("v:1.00\r\n", "")
    tmpText = ""
    for i in range(len(responseText)-1):
        tmpText += responseText[i]
        if(responseText[i] == "\n"):
            fileList.append(tmpText)
            tmpText = ""

    newList = []

    for item in fileList:
        newItem = item
        newItem = newItem.replace(",s:1000000", "")            
        newItem = newItem.replace("\r", "")            
        newItem = newItem.replace("\n", "")
        newItem = newItem.replace("n:", "")   
        newList.append(newItem)

    newList.sort()
    newList = await ignoreAlreadyDownloaded(newList)
    print(newList)

    return newList

async def writeToLog(fileName):
    print("fileName: " + fileName)
    with open("log.txt", "a") as f:
        f.write(fileName + ".mp4\n")
    return

async def ignoreAlreadyDownloaded(fileList: list):
    with open("log.txt", "r") as r:
        for line in r.readlines():
            blackvueFileName = "/Record/" + line
            blackvueFileName = blackvueFileName.replace("\n", "")
            if blackvueFileName in fileList:
                fileList.remove(blackvueFileName)

    return fileList

async def moveFileFromTmpToDestinationFolder():
    while(1):
        while(len(videoFileTransferList) == 0):
            await asyncio.sleep(5)
            print("waiting for file to be downloaded")

        availableSpace = await checkAvailableSpace(path=downloadFolder)
        while(availableSpace < 10):
            print(str(availableSpace) + r"% available")
            await asyncio.sleep(5)
            availableSpace = await checkAvailableSpace(path=downloadFolder)  
        
        videoFile: videoFileClass = videoFileTransferList[0]
        fileName = videoFile.fileName
        source = videoFile.source
        destination = videoFile.destination

        try:
            shutil.move(src=source, dst=destination)
            os.rename(src=destination, dst=destination+".mp4")
            await writeToLog(fileName)
            videoFileTransferList.remove(videoFile)

        except Exception as e:
            print(e, flush=True)
        
async def downloadFilesToTmpFolder():
    while(1):
        availableSpace = await checkAvailableSpace(path=tmpFolder)
        while(availableSpace < 20):
            print(str(availableSpace) + r"% available")
            await asyncio.sleep(5)
            availableSpace = await checkAvailableSpace(path=tmpFolder)          

        # retrieve sorted list of available videos from blackvue dashcam
        fileList = await getFileList()    

        # download first item in list
        video = fileList[0]        
        url = ip + str(video)
        newFileName = await newName(video)

        filePath = tmpFolder + newFileName
        destination = downloadFolder + "/" + newFileName
        
        print(filePath, flush=True)
        
        try:

            async with aiohttp.ClientSession() as session:
                async with session.get(url=url) as response:
                    with open(filePath, "wb") as newFile:
                        async for chunk in response.content.iter_chunked(4096):
                            newFile.write(chunk)                    

            videoFile = videoFileClass(fileName=newFileName, source=filePath, destination=destination)
            videoFileTransferList.append(videoFile)                             

        except Exception as e:
            os.remove(filePath)
            print(e, flush=True)

async def main():

    task = asyncio.create_task(downloadFilesToTmpFolder())
    task1 = asyncio.create_task(moveFileFromTmpToDestinationFolder())

    while(1):

        print("running")
        await asyncio.sleep(11)

asyncio.run(main())
