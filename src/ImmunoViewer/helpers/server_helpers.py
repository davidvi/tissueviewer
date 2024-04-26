import os
import json
import cv2
import numpy as np
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import asyncio

def mix_channels(images, chs, gains, color_mapping) -> np.ndarray:
    """
    Mixes multiple images into one by applying color mapping to each channel
    :param images: list of images to mix
    :param chs: list of channels to mix
    :param gains: list of gains to apply to each channel
    :param color_mapping: dictionary with color mapping
    :return: merged image
    """

    merged_image = np.zeros((*images[0].shape, 3), dtype=np.uint8)

    for image, ch, gain in zip(images, chs, gains):
        color_rgb = color_mapping[ch]
        enhanced_image = cv2.convertScaleAbs(image, alpha=gain)
        colored_image = cv2.merge([enhanced_image * (color_rgb[i] // 255) for i in range(3)])
        merged_image = cv2.add(merged_image, colored_image)

    return merged_image

def find_directories_with_files_folders(base_dir) -> list:
    """
    Finds all directories with _files suffix and returns them as a list of dictionaries
    :param base_dir: base directory to search in
    :return: list of dictionaries with directory name and files
    """
    directories_with_files = []

    for root, dirs, files in os.walk(base_dir):
        if root.count(os.sep) - base_dir.count(os.sep) >= 2:
            del dirs[:]
        for dirname in dirs:
            if dirname.endswith("_files"):
                buf = {}
                buf['name'] = os.path.relpath(root, base_dir)
                dirs.sort()
                buf['files'] = dirs
                directories_with_files.append(buf)

                buf['details'] = {}

                if os.path.isfile(os.path.join(f'{root}','sample.json')):
                        with open(os.path.join(f'{root}','sample.json'), 'r') as f:
                            data = json.load(f)
                            buf['details'] = data
                break
    return directories_with_files

def modify_dzi_format(dzi_file_path) -> str:
    """
    Modifies the DZI file format from TIFF to JPEG
    :param dzi_file_path: path to the DZI file
    :return: modified DZI file content
    """
    with open(dzi_file_path, 'r') as file:
        dzi_content = file.read()

    tree = ET.ElementTree(ET.fromstring(dzi_content))
    root = tree.getroot()

    if root.attrib['Format'].lower() == 'tiff':
        root.attrib['Format'] = 'jpeg'

    modified_dzi_str = ET.tostring(root, encoding='unicode')
    
    return modified_dzi_str