# Lighting Robustness
## Python Template Project for Auto Gamma Correction

This project is a template to be converted to mobile.

### Overview
The image enhancement aims to increase the mean brightness of an input image to a 
minimum level. Brightness is enhanced using gamma correction. The core routine of
this project computes the gamma parameter necessary to lift the brightness to a
predefined minimum value B_min.
Input images with mean brightness above B_min are not processed and therefore left unchanged.

### Files
The template project is located in a single python file, AutoGammaCorrect.py
The file contains the actual gammaCorrection incl. auto parameter computation, as well as an examplary main routine to 
run the gammaCorrection on a single input image (hard coded in __main__). Running the project takes no parameters.

### Gamma Correction
Gamma correction is a non-linear, pixelwise brightness transformation, in this case performed on a gray level image.
Brightness values must be in the range [0..1] (NOT [0..255] !).

    With a gamma value g in [0..1], a pixel (brightness) value b is transformed to:
    b -> b^g

