"""
Modified from: https://github.com/robertomest/neural-style-keras/blob/master/fast_style_transfer.py
Use a trained pastiche net to stylize images.
"""

import os
import numpy as np
import tensorflow as tf
import keras.backend as K
from keras.preprocessing.image import load_img, img_to_array
from keras.applications import vgg16
import h5py
import yaml
from model import pastiche_model
import time

class StyleTransfer(object):
    def __init__(self, checkpoint_path):
        config = tf.ConfigProto(device_count={"GPU": 0})
        session = tf.Session(config=config)
        K.set_session(session)
        
        # Strip the extension if there is one
        checkpoint_path = os.path.splitext(checkpoint_path)[0]
        with h5py.File(checkpoint_path + ".h5", "r") as f:
            model_args = yaml.load(f.attrs["args"])
            self.style_names = f.attrs["style_names"]

        self.print_with_date("Creating pastiche model...")
        class_targets = K.placeholder(shape=(None,), dtype=tf.int32)
        # Instantiate the model using information stored on tha yaml file
        pastiche_net = pastiche_model(None, width_factor=model_args.width_factor,
                                      nb_classes=model_args.nb_classes,
                                      targets=class_targets)
        with h5py.File(checkpoint_path + ".h5", "r") as f:
            pastiche_net.load_weights_from_hdf5_group(f["model_weights"])

        inputs = [pastiche_net.input, class_targets, K.learning_phase()]

        self.transfer_style = K.function(inputs, [pastiche_net.output])
    
    @staticmethod
    def post_process_image(img):
        img = img[0]
        # Remove zero-center by mean pixel
        img[:, :, 0] += 103.939
        img[:, :, 1] += 116.779
        img[:, :, 2] += 123.68
        # 'BGR'->'RGB'
        img = img[:, :, ::-1]
        img = np.clip(img, 0, 255).astype(np.uint8)
        return img

    def __call__(self, input_path, output_path, style_index):
        self.print_with_date("Processing {}".format(input_path))

        img = load_img(input_path)
        img = img_to_array(img)
        img = np.expand_dims(img, axis=0)
        img = vgg16.preprocess_input(img)

        indices = style_index + np.arange(1)
        names = [self.style_names[style_index]]
        style_name = names[0].decode("UTF-8")
        self.print_with_date("Using style {}".format(int(style_name)))

        output = self.transfer_style([np.repeat(img, 1, axis=0), indices, 0.])[0]
        output_img = self.post_process_image(output[0][None, :, :, :].copy())
        self.print_with_date("Transfer finished")

        return output_img

    @staticmethod
    def print_with_date(content):
        print("{} {}".format(time.asctime(), content))
