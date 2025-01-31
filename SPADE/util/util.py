from __future__ import print_function
# import torch
from PIL import Image
import cv2
import numpy as np
import os


# generate onehot like pytorch scatter_ operation
def scatter(out_array, dim, index, value): # a inplace
    expanded_index = [index if dim==i else np.arange(out_array.shape[i]).reshape([-1 if i==j else 1 for j in range(out_array.ndim)]) for i in range(out_array.ndim)]
    out_array[tuple(expanded_index)] = value

# get edge of instance map
def get_inst_map_edge(inst_nd):
    edge_nd = np.zeros(inst_nd.shape, dtype=np.uint8)
    edge_nd[:,:,:,1:] = edge_nd[:,:,:,1:] | (inst_nd[:,:,:,1:] != inst_nd[:,:,:,:-1])
    edge_nd[:,:,:,:-1] = edge_nd[:,:,:,:-1] | (inst_nd[:,:,:,1:] != inst_nd[:,:,:,:-1])
    edge_nd[:,:,1:,:] = edge_nd[:,:,1:,:] | (inst_nd[:,:,1:,:] != inst_nd[:,:,:-1,:])
    edge_nd[:,:,:-1,:] = edge_nd[:,:,:-1,:] | (inst_nd[:,:,1:,:] != inst_nd[:,:,:-1,:])
    return edge_nd

# def get_inst_map_edge(inst_nd):
#     edge_nd = np.zeros(inst_nd.shape, dtype=np.int32)
#     edge_nd[:,:,:,1:] += np.abs(inst_nd[:,:,:,1:] - inst_nd[:,:,:,:-1])
#     edge_nd[:,:,:,:-1] += np.abs(inst_nd[:,:,:,1:] - inst_nd[:,:,:,:-1])
#     edge_nd[:,:,1:,:] += np.abs(inst_nd[:,:,1:,:] - inst_nd[:,:,:-1,:])
#     edge_nd[:,:,:-1,:] += np.abs(inst_nd[:,:,1:,:] - inst_nd[:,:,:-1,:])
#     return edge_nd

# Converts a Tensor into a Numpy array
# |imtype|: the desired type of the converted numpy array
def tensor2im(image_tensor, imtype=np.uint8, normalize=True):
    if isinstance(image_tensor, list):
        image_numpy = []
        for i in range(len(image_tensor)):
            image_numpy.append(tensor2im(image_tensor[i], imtype, normalize))
        return image_numpy
    image_numpy = image_tensor
    if normalize:
        image_numpy = (np.transpose(image_numpy, (1, 2, 0)) + 1) / 2.0 * 255.0
    else:
        image_numpy = np.transpose(image_numpy, (1, 2, 0)) * 255.0
    image_numpy = np.clip(image_numpy, 0, 255)
    if image_numpy.shape[2] == 1 or image_numpy.shape[2] > 3:
        image_numpy = image_numpy[:,:,0]
    image_numpy = image_numpy.astype(imtype)
    image_numpy = cv2.cvtColor(image_numpy, cv2.COLOR_RGB2BGR)
    return image_numpy

# Converts a one-hot tensor into a colorful label map
def tensor2label(label_tensor, n_label, imtype=np.uint8):
    if n_label == 0:
        return tensor2im(label_tensor, imtype)
    if label_tensor.shape[0] > 1:
        label_tensor = np.max(label_tensor, axis=0, keepdims=True)
    label_tensor = Colorize(n_label)(label_tensor)
    return label_tensor.astype(imtype)

def onehot2label(one_hot_tensor, n_label, imtype=np.uint8):
    c, h, w = one_hot_tensor.shape
    for i in range(c):
        one_hot_tensor[i,:,:] *= i
    label_tensor = np.max(one_hot_tensor, axis=0, keepdims=True)
    label_tensor = Colorize(n_label)(label_tensor)
    return label_tensor.astype(imtype)

def save_image(image_numpy, image_path):
    image_pil = Image.fromarray(image_numpy)
    image_pil.save(image_path)

def mkdirs(paths):
    if isinstance(paths, list) and not isinstance(paths, str):
        for path in paths:
            mkdir(path)
    else:
        mkdir(paths)

def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

###############################################################################
# Code from
# https://github.com/ycszen/pytorch-seg/blob/master/transform.py
# Modified so it complies with the Citscape label map colors
###############################################################################
def uint82bin(n, count=8):
    """returns the binary of integer n, count refers to amount of bits"""
    return ''.join([str((n >> y) & 1) for y in range(count-1, -1, -1)])

def labelcolormap(N):
    if N == 35: # cityscape
        cmap = np.array([(  0,  0,  0), (  0,  0,  0), (  0,  0,  0), (  0,  0,  0), (  0,  0,  0), (111, 74,  0), ( 81,  0, 81),
                     (128, 64,128), (244, 35,232), (250,170,160), (230,150,140), ( 70, 70, 70), (102,102,156), (190,153,153),
                     (180,165,180), (150,100,100), (150,120, 90), (153,153,153), (153,153,153), (250,170, 30), (220,220,  0),
                     (107,142, 35), (152,251,152), ( 70,130,180), (220, 20, 60), (255,  0,  0), (  0,  0,142), (  0,  0, 70),
                     (  0, 60,100), (  0,  0, 90), (  0,  0,110), (  0, 80,100), (  0,  0,230), (119, 11, 32), (  0,  0,142)],
                     dtype=np.uint8)
    else:
        cmap = np.zeros((N, 3), dtype=np.uint8)
        for i in range(N):
            r, g, b = 0, 0, 0
            id = i
            for j in range(7):
                str_id = uint82bin(id)
                r = r ^ (np.uint8(str_id[-1]) << (7-j))
                g = g ^ (np.uint8(str_id[-2]) << (7-j))
                b = b ^ (np.uint8(str_id[-3]) << (7-j))
                id = id >> 3
            cmap[i, 0] = r
            cmap[i, 1] = g
            cmap[i, 2] = b
    return cmap

class Colorize(object):
    def __init__(self, n=35):
        self.cmap = labelcolormap(n)
        self.cmap = self.cmap[:n]

    def __call__(self, gray_image):
        size = gray_image.shape
        color_image = np.zeros((size[1], size[2], 3), dtype=np.uint8)

        for label in range(0, len(self.cmap)):
            mask = (label == gray_image[0])
            color_image[mask,:] = self.cmap[label]
        return color_image
