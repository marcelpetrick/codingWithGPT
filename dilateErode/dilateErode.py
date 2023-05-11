# Python program to demonstrate erosion and dilation of images.
import cv2
import numpy as np

# Reading the input image
img = cv2.imread('20230511.png', 0)

# Taking a matrix of size 5 as the kernel
kernel = np.ones((3, 3), np.uint8)

img_erosion = cv2.erode(img, kernel, iterations=1)
cv2.imwrite("erosion.png", img_erosion)

img_dilation = cv2.dilate(img_erosion, kernel, iterations=1)
cv2.imwrite("dilation.png", img_dilation)

# result is not what I planned to have :/
