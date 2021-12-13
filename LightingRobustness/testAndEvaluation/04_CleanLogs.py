'''
Run this script, to keep only log files in the log folder that have correponding images 
in the img folder.
log and img are the results written by gamm correction, filtered by RemoveBlackImages
'''

import os

#
# prepare
pathImg = "G:/LOGDATA_CPS/11_24/test/img"
pathLog = "G:/LOGDATA_CPS/11_24/test/log"
#
# collect
print("Collecting image files from ", pathImg)
imgFiles = [f for f in os.listdir(pathImg) if os.path.isfile(os.path.join(pathImg, f))]
print("Total number of images: ", len(imgFiles))
print("Collecting log files from ", pathLog)
logFiles = [f for f in os.listdir(pathLog) if os.path.isfile(os.path.join(pathLog, f))]
print("Total number of logs: ", len(logFiles))
print("diff = ",len(logFiles) -  len(imgFiles))
#
# filter file names
for i in range(0, len(imgFiles)):
    imgFiles[i] = imgFiles[i][0:imgFiles[i].find('_image')]
for i in range(0, len(logFiles)):
    logFiles[i] = logFiles[i][0:logFiles[i].find('_log')]
s1 = set(imgFiles)
s2 = set(logFiles)
diff = s2 - s1
print("Set diff = ", len(diff))
#
# removing
count = 0
for log in diff:
    name = os.path.join(pathLog, log + "_log.json")
    print(count, name)
    os.remove(name)
    count += 1

