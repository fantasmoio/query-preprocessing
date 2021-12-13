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
Gamma correction is a non-linear (power-law), pixelwise brightness transformation, in this case performed on a gray level image.
Brightness values must be in the range [0..1] (NOT [0..255] !).

    With a gamma value g in [0..1], a pixel (brightness) value b is transformed to:
    b -> b^g

Since b and g are in [0..1], b^g >= g, i.e. the brightness is enhanced. Gamma correction lifts darker values (small b) stronger than brighter ones. The smaller g, the stronger the effect.

For more information on gamma correction, see https://en.wikipedia.org/wiki/Gamma_correction

### Auto Parameter Computation
Gamma correction with a fixed parameter gamma leads to unwanted effects, e.g., already sufficiently bright images are further enhanced, introducing artefacts. A dynamic adaption of gamma is therefore necessary. It is hard to describe the brightness enhancement in terms of gamma. A more natural way is to define a minimum average image brightness level.

The auto parameter computation computes the gamma necessary to lift the mean brightness of the input image to a defined minimum B_min.
Input images with mean brightness above B_min are not processed and therefore left unchanged.

Gamma is computated using an iterative bi-section algorithm:

    # Initial Brightness Check
    Compute the image histogram H of the input image img
    Compute the mean brightness b_mean using H (= expected value of H)
    If b_mean >= b_min => return
    # Init gamma and bisection
    gamma = 1.0
    step = 0.5
    Loop:
        if b_mean close enough to b_min: break
        if b_mean < b_min: gamma -= step
        if b_mean > b_min: gamma += step
        stp /= 2
        adjust bin-values v of H (v->v^gamma)
        Compute the mean brightness b_mean using H
    
    do gamma correction: img->img^gamma
        
Remarks:
- Using the histogram for brightness computation is massively faster than using the image itself: 
In the loop, updating the image only takes (number of bins) operations, instead (number of pixels)
- The iteration ends, when the brightness is 'close enough' to the min, which is defined as +/- 1%, i.e.
    updated brightness is in the interval meanRange = (b_mean - b_mean/100.0, b_mean + b_mean/100.0)
