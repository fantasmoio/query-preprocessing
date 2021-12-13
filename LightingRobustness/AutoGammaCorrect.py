'''
Gamma correction method for query images. gammaCorrect lifts the brightness
of an input image using gamma (or power) correction. Gamma is computed such
that the resulting mean image brightness matches a given value.
Images with higher brightness than the target brightness are excluded.

This code is a template, meant to be converted to a mobile device language.
The MAIN part gives an example of how to call the method.
'''

import sys
import numpy as np
import cv2 as cv


'''
Gamma-correct image to receive a brightness mean of <meanT> (+/- 1%)
Only images darker (lower mean) than meanT are processed.
Image data must be numpy array in [0..1].
Mean is computed through histogram for performance reasons.
Target meanT is approximated by simple bisection of gamma in [0..1].
'''
def gammaCorrect(img, meanT):
    # a numpy histogram consists of 2 arrays,
    # 0: the actual histogram (i.e., the count values)
    # 1: the bin-edge values (here: (0,1/256,2/256,..,1.0))
    hist = np.histogram(img, bins=256, range = (0.0, 1.0))
    sumHist = np.sum(hist[0])
    # mean brightness of image
    meanHist = np.sum(hist[1][0:-1] * hist[0]) / sumHist
    #
    # Image brighter than thresh? Don't process.
    if ( meanHist >= meanT):
        return img
    #
    # numpy places the bin values into h[1]. Store the 
    # original bin values to alter them by ^gamma below.
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
    print(gamma)
    return img

########################################################
# MAIN
if __name__ == '__main__':
    # open and convert to grayscale, range [0..1]
    image = cv.imread("data/img2.png")
    image = cv.cvtColor(image, cv.COLOR_BGR2GRAY) / 255.0
    #
    # gamma correct with target mean brightness of (at least) 0.15
    imageCorr = gammaCorrect(image, 0.15)
    #
    # show
    stacked = np.hstack((image, imageCorr))
    cv.imshow('Grayscale', stacked)
    cv.waitKey(0)