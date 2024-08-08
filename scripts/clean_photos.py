#!/usr/bin/python
# -*- coding: utf-8 -*-

# import some common detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog
import cv2
import pandas as pd
import os
import csv
from sys import argv



# workflow
# 1 de lijst met bestandsnamen (csv) wordt uitgelezen
# 2 op de foto wordt gekeken of er 1 of meer mensen op de foto staan
# 3 indien 1, dan zetten we deze in een map portrets
#   indien 0, dan zetten we deze in een map empty
#   indien meerdere, dan zetten we deze in een map group
# 4 als controle maken we een overzichtscsv

cfg = get_cfg()
treshold = 0.7
source_csv = argv[1]
has_subdirectories = argv[2]


# lines bestaat uit: index nr, filename, aantal gezichten
lines = [["filename", "location", "aantal gezichten"]]

def create_dirs(directory):
    if not os.path.exists("{}/portrets".format(directory)):
        os.makedirs("{}/portrets".format(directory))
        os.mkdir("{}/empty".format(directory))
        os.mkdir("{}/group".format(directory))


# setup detection model
def setup_detection_model(treshold): 
    print("setting up model")  
    cfg.MODEL.DEVICE = 'cpu'
    cfg.merge_from_file(model_zoo.get_config_file(
        "COCO-Keypoints/keypoint_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = treshold  # set threshold for this model
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(
        "COCO-Keypoints/keypoint_rcnn_R_50_FPN_3x.yaml")
    predictor = DefaultPredictor(cfg)
    print("done with setting up model")
    return predictor

def write_data(directory, data):
    print("writing data")
    with open("{}/cleanup_portrets.csv".format(directory), "w") as output_csv:
        csv_writer = csv.writer(output_csv)
        csv_writer.writerows(data)
    output_csv.close()
   
def is_portret(predictor, photo):
    print("is {} a portret?".format(photo))
    try:
        image = cv2.imread(photo)
        outputs = predictor(image)
        instances = outputs["instances"]
        count_instances = len(instances)

        directory, filename = os.path.split(str(photo))
        
        if  count_instances == 1:
            print("one instance found on " + str(photo))
            location = get_location(directory, "portrets")
            is_portret = True

        elif count_instances == 0:
            print("zero instances found on " + str(photo))
            location = get_location(directory, "empty")
            is_portret = False

        else: 
            print("multiple instances found on " + str(photo))
            location = get_location(directory, "group")
            is_portret = False
        
        filepath = "{}/{}".format(location, filename)

        if not os.path.exists(location):
            os.makedirs(location)
        os.rename(str(photo), filepath)
        lines.append([filename, filepath, count_instances])

        return is_portret
    
    except Exception as error:
        print(error)
        return
    
def get_location(directory, name):
    if has_subdirectories:
        head, subdir = os.path.split(directory)
        return "{}/{}/{}".format(head, name, subdir)
    else:
        return "{}/{}".format(directory, name)

predictor = setup_detection_model(treshold)
list_photos = pd.read_csv(source_csv, delimiter='\t').values.tolist()
directory, filename = os.path.split(list_photos[0][0])

if has_subdirectories:
    head, subdir = os.path.split(directory)
    location = head
else:
    location = directory

create_dirs(location)

for photo in list_photos:
    filename = photo[0].split('/')[-1]
    print(filename)
    if is_portret(predictor, photo[0]):
        print("{} is a portret".format(filename))
    else:
        print("{} is not a portret".format(filename))

write_data(location, lines)