'''
Test if adaptive equalization has advantages over gamma correction. Result: not for our purposes.
This code is therefore obsolete.
'''


import sys
import numpy as np
import cv2 as cv
from AutoGammaCorrect import gammaCorrect

########################################################
# MAIN
if __name__ == '__main__':
    # open and convert to grayscale, range [0..1]
    image = cv.imread("data/img1.png")
    image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    #
    gc = gammaCorrect(image/255.0, 0.15)
    clahe = cv.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
    cl1 = clahe.apply(image)
    #
    # show
    stacked = np.hstack((image, cl1, (gc * 255).astype(np.uint8)))
    cv.imshow('Grayscale', stacked)
    cv.waitKey(0)