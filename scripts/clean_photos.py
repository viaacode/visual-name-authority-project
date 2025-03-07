#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import csv
from sys import argv

# import some common detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
import cv2
import pandas as pd


# workflow
# 1 de lijst met bestandsnamen (csv) wordt uitgelezen
# 2 op de foto wordt gekeken of er 1 of meer mensen op de foto staan
# 3 indien 1, dan zetten we deze in een map portrets
#   indien 0, dan zetten we deze in een map empty
#   indien meerdere, dan zetten we deze in een map group
# 4 als controle maken we een overzichtscsv

# constants
TRESHOLD = 0.7
SOURCE_CSV = argv[1]
HAS_SUBDIRECTORIES = argv[2]

# variables
cfg = get_cfg()
lines = [["filename", "location", "aantal gezichten"]]

def create_dirs(directory: str):
    if not os.path.exists(f"{directory}/portrets"):
        os.makedirs(f"{directory}/portrets")
        os.mkdir(f"{directory}/empty")
        os.mkdir(f"{directory}/group")


# setup detection model
def setup_detection_model():
    print("setting up model")
    cfg.MODEL.DEVICE = 'cpu'
    cfg.merge_from_file(model_zoo.get_config_file(
        "COCO-Keypoints/keypoint_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = TRESHOLD  # set threshold for this model
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(
        "COCO-Keypoints/keypoint_rcnn_R_50_FPN_3x.yaml")
    print("done with setting up model")
    return DefaultPredictor(cfg)

def write_data(directory: str, data):
    print("writing data")
    with open(f"{directory}/cleanup_portrets.csv", "w", encoding="utf-8") as output_csv:
        csv_writer = csv.writer(output_csv)
        csv_writer.writerows(data)
    output_csv.close()

def is_portret(predictor: DefaultPredictor, photo: str):
    print(f"is {photo} a portret?")
    directory, filename = os.path.split(str(photo))

    try:
        image = cv2.imread(photo)
        outputs = predictor(image)
        instances = outputs["instances"]
        count_instances = len(instances)

        if  count_instances == 1:
            print("one instance found on " + str(photo))
            location = get_location(directory, "portrets")
            portret = True

        elif count_instances == 0:
            print("zero instances found on " + str(photo))
            location = get_location(directory, "empty")
            portret = False

        else:
            print("multiple instances found on " + str(photo))
            location = get_location(directory, "group")
            portret = False

        filepath = f"{location}/{filename}"

        if not os.path.exists(location):
            os.makedirs(location)
        os.rename(str(photo), filepath)
        lines.append([filename, filepath, count_instances])

        return portret

    except Exception as error:
        print(error)
        # remove images that can't be read
        os.remove(photo)
        return

def get_location(directory, name):
    if HAS_SUBDIRECTORIES:
        head, subdir = os.path.split(directory)
        return f"{head}/{name}/{subdir}"
    return f"{directory}/{name}"


def clean_photos():
    # lines bestaat uit: index nr, filename, aantal gezichten
    predictor = setup_detection_model()
    list_photos = pd.read_csv(SOURCE_CSV, delimiter='\t').values.tolist()
    directory, filename = os.path.split(list_photos[0][0])

    if HAS_SUBDIRECTORIES:
        head = os.path.split(directory)[0]
        location = head
    else:
        location = directory

    create_dirs(location)

    for photo in list_photos:
        filename = photo[0].split('/')[-1]
        print(filename)
        if is_portret(predictor, photo[0]):
            print(f"{filename} is a portret")
        else:
            print(f"{filename} is not a portret")

    write_data(location, lines)
    print(location)

if __name__ == "__main__":
    clean_photos()
