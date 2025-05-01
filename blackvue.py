import os
import requests
import shutil
import asyncio
import subprocess

from dotenv import load_dotenv

load_dotenv()

ip = os.getenv("blackvueIP")
downloadFolder = os.getenv("downloadFolder")
tmpFolder= os.getenv("tmpFolder")
print(ip, flush=True)

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

async def main():
    while(1):

        fileList = await getFileList()

        for item in fileList:
            url = ip + str(item)
            newFileName = await newName(item)
            filePath = tmpFolder + newFileName
            print(filePath, flush=True)
            try:
                with requests.get(url=url, stream=True) as videoFile:
                    videoFile.raise_for_status()
                    
                    with open(filePath, "wb") as newFile:
                        for chunk in videoFile.iter_content(chunk_size=4096):
                            newFile.write(chunk)

                destination = downloadFolder + "/" + newFileName

                availableSpace = 0
                while(availableSpace < 10):
                    print(str(availableSpace) + r"% available")
                    await asyncio.sleep(5)
                    availableSpace = await checkAvailableSpace(path=downloadFolder)                

                try:
                    shutil.move(src=newFile.name, dst=destination)
                    os.rename(src=destination, dst=destination+".mp4")
                    await writeToLog(newFileName)
                except Exception as e: 
                    print(e, flush=True)

            except Exception as e:
                print(e, flush=True)

asyncio.run(main())
