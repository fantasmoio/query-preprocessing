import numpy as np
import cv2 as cv
from os import listdir, remove, mkdir
from os.path import isfile, join, isdir
import sys
import json

''' ---------------------------------------------------------------------------
Check Directory Structure
Checks for subdirectories 'logs', 'masked_images', 'masks'
Creates subfolder 'test'
'''
def checkDirectories(parentDir):
    ok = isdir(parentDir + "/logs")
    ok = ok and isdir(parentDir + "/masked_images")
    ok = ok and isdir(parentDir + "/masks")
    if ok:
        if not isdir(parentDir + "/test"):
            mkdir(parentDir + "/test")
            mkdir(DIRECTORY + "/test/log")
            mkdir(DIRECTORY + "/test/img")
    return ok

''' ---------------------------------------------------------------------------
Check for triplets, i.e. images that exist in logs, masked_images and masks
Removes incomplete (i.e., not element in a triplet) files.
Assumes subfolders logs, masked_images, masks (as created by data download).
Returns base names of triplets.
'''
def checkForTriplets(DIRECTORY):
    path = DIRECTORY + '/' + "masks"
    print("Collecting files from ", path)
    maskFiles = [f for f in listdir(path) if isfile(join(path, f))]
    path = DIRECTORY + '/' + "logs"
    print("Collecting files from ", path)
    logFiles = [f for f in listdir(path) if isfile(join(path, f))]
    path = DIRECTORY + '/' + "masked_images"
    print("Collecting files from ", path)
    imageFiles = [f for f in listdir(path) if isfile(join(path, f))]
    #
    # remove extensions
    logSet = set()
    imgSet = set()
    mskSet = set()
    print("Creating log set")
    for logFile in logFiles:
        name = logFile[0:logFile.find('_log')]
        logSet.add(name)
    print("Creating image set")
    for imageFile in imageFiles:
        name = imageFile[0:imageFile.find('_image_masked')]
        imgSet.add(name)
    print("Creating mask set")
    for maskFile in maskFiles:
        name = maskFile[0:maskFile.find('_mask')]
        mskSet.add(name)
    # create triplets
    print("Creating triplets")
    triplets = mskSet & logSet & imgSet
    # get incomplete files
    logFail = logSet - triplets
    imgFail = imgSet - triplets
    mskFail = mskSet - triplets
    # complete filenames and collect
    print("Prepare cleanup")
    failed = []
    for name in logFail:
        failed.append(DIRECTORY + '/' + "logs/" + name + "_log.json")
    for name in imgFail:
        failed.append(DIRECTORY + '/' + "masked_images/" + name + "_image_masked.jpg")
    for name in mskFail:
        failed.append(DIRECTORY + '/' + "masks/" + name + "_mask.jpg")
    # remove files
    print("clean, remove unnecessary files")
    for fail in failed:
        remove(fail)
    #
    # good bye
    return triplets

# -----------------------------------------------------------------------------
# Gamma correction with masks
def gammaCorrect(img, mask, meanT):
    hist = np.histogram(img, bins=256, range = (0.0, 1.0))
    #
    # ---
    # take mask into consideration: this is only for testing
    # lift brightness of image by 1/256, to reserve 0 for mask
    # the resulting brightness shift is unimportant
    binEdge0 = hist[1][1] + 1e-10
    img = np.minimum(img + binEdge0, np.ones(img.shape))
    img = np.minimum(img, mask)
    histM = np.histogram(img, bins=256, range = (0.0, 1.0))
    histM[0][0] = 0
    hist = histM
    # ---
    #
    sumHist = np.sum(hist[0])
    meanHist = np.sum(hist[1][0:-1] * hist[0]) / sumHist
    #
    # Image brighter than thresh? Don't process.
    if ( meanHist >= meanT):
        return img, 1.0
    #
    histOrig = hist[1][0:-1]
    # target brightness range: meanT +/- 1 percent
    meanRange = (meanT - meanT/100.0, meanT + meanT/100.0)
    # initialize bisection
    gamma = 1.0
    stp = 0.5
    #
    # bisection loop
    while True:
        # close enough: done.
        if meanHist >= meanRange[0] and meanHist <= meanRange[1]:
            break
        # otherwise: adjust gamma
        if meanHist < meanT:
            gamma -= stp
        else:
            gamma += stp
        stp /= 2
        # compute new mean
        hCorrected = np.power(histOrig, gamma)
        meanHist = np.sum(hCorrected * hist[0]) / sumHist
    # change image
    img = np.power(img, gamma)
    return img, gamma

''' ---------------------------------------------------------------------------
Save Image and logfile
'''
def saveData(dir, name, gamma):
    imgNameOut = dir + "/test/img/" + name + "_image_masked.jpg"
    imgNameIn = dir + "/masked_images/" + name + "_image_masked.jpg"
    logNameOut = dir + "/test/log/" + name + "_log.json"
    logNameIn = dir + "/logs/" + name + "_log.json"
    #
    # load, augment and save json
    # adds "note" field to json
    with open(logNameIn) as f:
        data = json.load(f)
        responseCode = data["response"]["responseCode"]
        augmentDict = {"test":"yes", "name":name, "gamma":gamma, "code":responseCode}
        data['note'] = augmentDict
    with open(logNameOut, 'w') as json_file:
        json.dump(data, json_file)
    #
    # load, enhance and save image    
    img = cv.imread(imgNameIn)
    img = cv.cvtColor(img, cv.COLOR_BGR2GRAY) / 255.0
    img = np.power(img, gamma)
    cv.imwrite(imgNameOut, img * 255)

########################################################
# MAIN
if __name__ == '__main__':
    SHOW = False

    # check args
    numArgs = len(sys.argv) - 1
    if numArgs == 0:
        DIRECTORY = "G:/LOGDATA_CPS/11_24"
    elif numArgs == 1:
        DIRECTORY = sys.argv[1]
    else:
        print("Usage: TestGammaCorrection <directory>")
        
    #
    # check directories
    if not checkDirectories(DIRECTORY):
        print("Failed to find required directory structure.")
        sys.exit(-1)
    #
    # data cleaning
    print("Cleaning Data")
    triplets = checkForTriplets(DIRECTORY)
    print(len(triplets), " files remaining")
    #
    # for each triplet...
    for name in triplets:
        logName = DIRECTORY + '/' + "logs/" + name + "_log.json"
        imgName = DIRECTORY + '/' + "masked_images/" + name + "_image_masked.jpg"
        mskName = DIRECTORY + '/' + "masks/" + name + "_mask.jpg"
        #
        # open and convert to grayscale, range [0..1]
        image = cv.imread(imgName)
        image = cv.cvtColor(image, cv.COLOR_BGR2GRAY) / 255.0
        mask = cv.imread(mskName)
        mask = cv.cvtColor(mask, cv.COLOR_BGR2GRAY)
        #
        # gamma correct with target mean brightness of (at least) 0.15
        imageNew, gamma = gammaCorrect(image, mask, 0.15)
        print(name, gamma)
        #
        # show
        if SHOW and gamma < 1.0:
            stacked = np.hstack((image, imageNew))
            cv.imshow('Grayscale', stacked)
            cv.waitKey(0)
        #
        # save
        if gamma < 1.0:
            saveData(DIRECTORY, name, gamma)

