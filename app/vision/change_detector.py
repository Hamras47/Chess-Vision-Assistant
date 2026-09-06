"""Non-semantic whole-board image change trigger for AI-first tracking."""
import cv2
import numpy as np

def frame_signature(image,size=16):
    return cv2.resize(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),(size,size),interpolation=cv2.INTER_AREA)

def signature_difference(before,after):
    return float(np.mean(cv2.absdiff(before,after))/255)
