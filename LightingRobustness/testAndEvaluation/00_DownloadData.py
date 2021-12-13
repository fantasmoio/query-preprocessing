# Gordan's download/analysis program
# Example call:
# python 00_DownloadData.py --date_begin 2021-10-26 --download --images --destination ./LOGDATA




import argparse
import sys
import re
import pandas
from datetime import datetime
from datetime import date
import os
import json
from vincenty import vincenty
import statistics
import math
import csv

allowedArcDistance = 100.0

class Session:
    def __init__(self):
        self.logs = []

    def print(self):
        print("\n=====SESSION=====")
        for log in self.logs:
            print("----------")
            log.print()
            print("----------")
        print("=================\n")
    
    def printIndices(self):
        print("\n=====SESSION=====")
        for log in self.logs:
            print(log.imagePath)
        print("=================\n")

    def getSessionLocalizationInfo(self):
        for log in self.logs:
            if log.responseCode == 200:
                timeToLocalize = log.timestamp - self.logs[0].timestamp
                return (timeToLocalize, True)
        
        sessionTime = self.logs[-1].timestamp - self.logs[0].timestamp
        return (sessionTime, False)

class Log:
    def __init__(self, fileName, lat, long, mapID, responseCode, timestamp, imagePath, sessionID = None):
        self.fileName = fileName
        self.coordinate = [lat, long]
        self.mapID = mapID
        self.responseCode = responseCode
        self.sessionID = sessionID
        if timestamp > 2000000000:
            timestamp = timestamp/1000.0
        self.timestamp = timestamp
        self.imagePath = imagePath
        self.assigned = False
        self.returnCoordinate = None
    
    def print(self):
        print("File name: ", self.fileName)
        print("Lat: ", self.coordinate[0])
        print("Long: ", self.coordinate[1])
        print("MapID: ", self.mapID)
        print("ResponseCode: ", self.responseCode)
        print("Timestamp: ", self.timestamp)
        print("SessionID: ", self.sessionID)
        print("ImagePath: ", self.imagePath)
        print("Index: ", self.index)
        print("Return coordinate: ", self.returnCoordinate)
    
    def setReturnCoordinate(self, lat, long):
        self.returnCoordinate = [lat, long]

def getDatesList(begin, end):
    beginDate = checkStringFormatting(begin)
    endDate = checkStringFormatting(end)

    [by, bm, bd] = beginDate.split("-")
    [ey, em, ed] = endDate.split("-")
    
    beginningDate = date(int(by), int(bm), int(bd))
    endingDate = date(int(ey), int(em), int(ed))
    
    allDates = pandas.date_range(beginningDate, endingDate)

    allDatesAsStr = allDates.astype(str)

    return allDatesAsStr


def checkStringFormatting(s):
    correct = re.findall("\d\d\d\d-\d\d-\d\d", s)
    if len(correct) != 0:
        return correct[0]
    else:
        print("The date string:")
        print(s)
        print("doesn't have correct formattting. Please use YYYY-MM-DD")
        exit(0)

def downloadLoggingData(beginDate, endDate, images, destination, account, source):
    
    allDates = getDatesList(beginDate, endDate)

    for d in allDates:
        # inserted: load masks
        command = ("az storage blob download-batch --destination {} --pattern \"masks/{}*\" --account-name {} --source {}".format(destination, d, account, source))
        os.system(command)
        # end insertion
        command = ("az storage blob download-batch --destination {} --pattern \"logs/{}*\" --account-name {} --source {}".format(destination, d, account, source))
        os.system(command)
        if images:
            command = ("az storage blob download-batch --destination {} --pattern \"masked_images/{}*\" --account-name {} --source {}".format(destination, d, account, source))
            os.system(command)

def processLoggingData(path, spotID, beginDate, endDate):
    allDates = getDatesList(beginDate, endDate)

    allLogs = []
    logsPath = os.path.join(path, "logs")
    for file in sorted(os.listdir(logsPath)):
        if file.endswith(".json") and not file.startswith("."):
            if file.startswith(tuple(allDates)):
                fullFilePath = os.path.join(logsPath, file)
                with open(fullFilePath) as jsonFile:
                    data = json.load(jsonFile)
                    if 'request' in data and 'response' in data and 'mapID' in data and 'url' in data:
                        if 'coordinate' in data['request'] and 'timestamp' in data['request'] and 'responseCode' in data['response']:
                            lat = data['request']['coordinate']['latitude']
                            long = data['request']['coordinate']['longitude']
                            code = data['response']['responseCode']
                            mapID = data['mapID']
                            timestamp = data['request']['timestamp']
                            imageName = data['url'].split("/")[-1]
                            retLat = None
                            retLong = None
                            imagePath = os.path.join(os.path.join(path, "masked_images"), imageName)
                            if 'location' in data['response']['responseContent']:
                                retLat = data['response']['responseContent']['location']['coordinate']['latitude']
                                retLong = data['response']['responseContent']['location']['coordinate']['longitude']
                            if spotID is None:
                                log = Log(file, lat, long, mapID, code, timestamp, imagePath)
                                if retLat is not None and retLong is not None:
                                    log.setReturnCoordinate(retLat, retLong)
                                allLogs.append(log)
                            elif mapID.startswith(spotID + "_"):
                                log = Log(file, lat, long, mapID, code, timestamp, imagePath)
                                if retLat is not None and retLong is not None:
                                    log.setReturnCoordinate(retLat, retLong)
                                allLogs.append(log)    
    return allLogs

def getDistanceInMeters(coord1, coord2):
    distanceInMeters = vincenty((coord1[0], coord1[1]), (coord2[0], coord2[1]))*1000.0
    return distanceInMeters

def distributeDataToSessions(logList, index):

    # TODO: Think about these two thresholds, perhaps consult with Lucas and Ryan
    secondsThreshold = 5.0
    distanceThreshold = 100.0
    sess = Session()

    if index == -1:
        return []
    
    if logList[index].assigned:
        print("error")
        exit()

    prevTimestamp = logList[index].timestamp
    prevCoordinate = logList[index].coordinate
    prevMapID = logList[index].mapID
    logList[index].assigned = True
    sess.logs.append(logList[index])

    nextSessionStartingIndex = -1

    for i in range(index+1, len(logList)):
        thisTimestamp = logList[i].timestamp
        thisCoordinate = logList[i].coordinate
        thisMapID = logList[i].mapID
        if thisTimestamp - prevTimestamp > secondsThreshold:
            # We have not encountered a new log for a certain threshold, so we assume that the session is over
            # We recursively call the next session creation and return the current session to be added to the list
            allFutureSessions = []
            if nextSessionStartingIndex == -1:
                for j in range(i, len(logList)):
                    if not logList[j].assigned:
                        allFutureSessions = distributeDataToSessions(logList, j)
                        break
            else:
                allFutureSessions = distributeDataToSessions(logList, nextSessionStartingIndex)
            allFutureSessions.insert(0, sess)
            return allFutureSessions
            #break
        elif thisMapID == prevMapID and getDistanceInMeters(thisCoordinate, prevCoordinate) < distanceThreshold and not logList[i].assigned:
            # Found new item in the logs for the current session
            prevTimestamp = thisTimestamp
            prevCoordinate = thisCoordinate
            sess.logs.append(logList[i])
            logList[i].assigned = True
        else:
            # We have encountered a new session
            if not logList[i].assigned:
                if nextSessionStartingIndex == -1:
                    nextSessionStartingIndex = i
    
    return [sess]

def mapSessionsToIDs(sessionList):
    mapDict = {}
    for i in range(0, len(sessionList)):
        sess = sessionList[i]
        mapID = sess.logs[0].mapID
        if mapID in mapDict:
            list  = mapDict[mapID]
            list.append(i)
            mapDict[mapID] = list
        else:
            mapDict[mapID] = [i]
    
    return mapDict

def getStatistics(mapID, sessionList):
    totalNumberOfLogs = 0
    successfulSessionTimes = []
    unsuccessfulSessionTimes = []
    allSessionTimes = []
    for sess in sessionList:
        totalNumberOfLogs = totalNumberOfLogs + len(sess.logs)

        (sessionTime, sessionSuccess) = sess.getSessionLocalizationInfo()
        if sessionSuccess:
            successfulSessionTimes.append(sessionTime)
        else:
            unsuccessfulSessionTimes.append(sessionTime)
        allSessionTimes.append(sessionTime)
    
    numberOfSessions = len(sessionList)
    numberOfSuccessfulSessions = len(successfulSessionTimes)
    numberOfUnsuccessfulSessions = len(unsuccessfulSessionTimes)
    percentOfSuccessfulSessions = 100.0*numberOfSuccessfulSessions/numberOfSessions
    meanSuccessfulSessionTime = "N/A"
    medianSuccessfulSessionTime = "N/A"
    meanUnsuccessfulSessionTime = "N/A"
    medianUnsuccessfulSessionTime = "N/A"
    if numberOfSuccessfulSessions > 0:
        meanSuccessfulSessionTime = statistics.mean(successfulSessionTimes)
        medianSuccessfulSessionTime = statistics.median(successfulSessionTimes)
    if numberOfUnsuccessfulSessions > 0:
        meanUnsuccessfulSessionTime = statistics.mean(unsuccessfulSessionTimes)
        medianUnsuccessfulSessionTime = statistics.median(unsuccessfulSessionTimes)
    totalMeanTime = statistics.mean(allSessionTimes)
    totalMedianTime = statistics.median(allSessionTimes)

    #print("Total number of logs for this session: ", totalNumberOfLogs)
    #print("The total number of sessions: ", len(sessionList))
    #print("Successful sessions: ", len(successfulSessionTimes))
    #print("Successful sessions percentage: ", 100.0*len(successfulSessionTimes)/len(sessionList))
    #if(len(successfulSessionTimes) > 0):
    #    print("Mean successful session time: ", statistics.mean(successfulSessionTimes))
    #    print("Median successful session time: ", statistics.median(successfulSessionTimes))
    #print("Unsuccessful sessions: ", len(unsuccessfulSessionTimes))
    #if(len(unsuccessfulSessionTimes) > 0):
    #    print("Mean unsuccessful session time: ", statistics.mean(unsuccessfulSessionTimes))
    #    print("Median unsuccessful session time: ", statistics.median(unsuccessfulSessionTimes))
    #print("All sessions: ", len(allSessionTimes))
    #print("Mean session time: ", statistics.mean(allSessionTimes))
    #print("Median session time: ", statistics.median(allSessionTimes))

    # KPI-Specific
    sessionsWithin2Seconds = 0
    sessionsWithin5Seconds = 0
    for t in allSessionTimes:
        if t < 2.0:
            sessionsWithin2Seconds = sessionsWithin2Seconds + 1
        if t < 5.0:
            sessionsWithin5Seconds = sessionsWithin5Seconds + 1
    
    kpi1 = 100.0 * sessionsWithin2Seconds/len(allSessionTimes)
    kpi2 = 100.0 * sessionsWithin5Seconds/len(allSessionTimes)
    
    #print("Percentage of sessions finished within 2 seconds: ", 100.0 * sessionsWithin2Seconds/len(allSessionTimes))
    #print("Percentage of sessions finished within 5 seconds: ", 100.0 * sessionsWithin5Seconds/len(allSessionTimes))
    #print("====================\n")

    return (numberOfSessions, percentOfSuccessfulSessions, meanSuccessfulSessionTime, medianSuccessfulSessionTime, meanUnsuccessfulSessionTime, medianUnsuccessfulSessionTime, totalMeanTime, totalMedianTime, kpi1, kpi2)

def checkForArcs(logList):
    for log in logList:
        if log.responseCode == 200:
            if log.returnCoordinate is not None:
                arcLength = getDistanceInMeters(log.coordinate, log.returnCoordinate)
                if arcLength > allowedArcDistance:
                    print("Arc length too long for timestamp ", log.timestamp)
                    print(arcLength)
                    log.print()
                else:
                    print("Arc length good for timestamp ", log.timestamp)
                    print(arcLength)

def parseArgs(argv):
    parser = argparse.ArgumentParser(description='Query the localize API.')
    parser.add_argument('--date_begin', required=True, help='From what date to start downloading log files (inclusive). Format YYYY-MM-DD.')
    parser.add_argument('--date_end', required=False, help='Until what date to download log files (inclusive). Format YYYY-MM-DD. Default is the current date.')
    parser.add_argument('--account', required=False, default='loggingdata', help='the account where the data is stored. Defaults to loggingdata')
    parser.add_argument('--container', required=False, default='cpslogs', help='the container where the data is stored. Defaults to cpslogs')
    parser.add_argument('--spotID', required=False, help='in case we want to get statistics for a particular spot, add the spot id here')

    parser.add_argument('--images', help='whether to also download the masked images. Defaults to false', action='store_true')
    parser.add_argument('--destination', required=True, help='The downloading destination')
    parser.add_argument('--download', required=False, help="Whether we will download data", action='store_true')

    return parser.parse_args(argv[1:])

def writeReport(allSessions, outputDirectory, beginDate, endDate):
    with open(os.path.join(outputDirectory, "report_" + beginDate + "_" + endDate + ".csv"), mode='w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        
        csvwriter.writerow(["MapID", "Number of sessions", "Percent of successful sessions", "Mean Successful Session Time", "Median Successful Session Time", "Mean Unsuccessful Session Time", "Median Unsuccessful Session Time", "Total Mean Time", "Total Median Time", "Percent of sessions ending within 2 seconds", "Percent of sessions ending within 5 seconds"])

        (numberOfSessions, percentOfSuccessfulSessions, meanSuccessfulSessionTime, medianSuccessfulSessionTime, meanUnsuccessfulSessionTime, medianUnsuccessfulSessionTime, totalMeanTime, totalMedianTime, kpi1, kpi2) = getStatistics("All maps", allSessions)

        csvwriter.writerow(["All maps", numberOfSessions, percentOfSuccessfulSessions, meanSuccessfulSessionTime, medianSuccessfulSessionTime, meanUnsuccessfulSessionTime, medianUnsuccessfulSessionTime, totalMeanTime, totalMedianTime, kpi1, kpi2])

        # Get per-spot statistics
        map = mapSessionsToIDs(allSessions)
        for element in map:
            sessionSubset = []
            for index in map[element]:
                sessionSubset.append(allSessions[index])
            (numberOfSessions, percentOfSuccessfulSessions, meanSuccessfulSessionTime, medianSuccessfulSessionTime, meanUnsuccessfulSessionTime, medianUnsuccessfulSessionTime, totalMeanTime, totalMedianTime, kpi1, kpi2) = getStatistics(element, sessionSubset)
            csvwriter.writerow([element, numberOfSessions, percentOfSuccessfulSessions, meanSuccessfulSessionTime, medianSuccessfulSessionTime, meanUnsuccessfulSessionTime, medianUnsuccessfulSessionTime, totalMeanTime, totalMedianTime, kpi1, kpi2])

'''---------------------------------------------------------------------------------------------------------------------------
MAIN
'''
def main():
    sys.setrecursionlimit(10000)
    args = parseArgs(sys.argv)

    if args.date_end is None:
        args.date_end = datetime.today().strftime('%Y-%m-%d')

    if args.download:
        downloadLoggingData(args.date_begin, args.date_end, args.images, args.destination, args.account, args.container)
    
    allLogs = processLoggingData(args.destination, args.spotID, args.date_begin, args.date_end)
    
    allSessions = distributeDataToSessions(allLogs, 0)

    print(len(allLogs))
    writeReport(allSessions, args.destination, args.date_begin, args.date_end)
    
    #checkForArcs(allLogs)    
    
    


if __name__ == "__main__":
    main()