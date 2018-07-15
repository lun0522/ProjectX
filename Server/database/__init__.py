import os.path

from .paintingDB import PaintingDatabaseHandler
from .modelDB import ModelDatabaseHandler

__all__ = ["PaintingDatabaseHandler", "ModelDatabaseHandler",
           "downloads_dir", "paintings_dir", "faces_dir", "temp_dir",
           "models_dir", "predictor_path", "style_path",
           "svm_path", "dataset_dir", "emotions", "emotions_dir"]

resource_dir   = "/Users/lun/Desktop/ProjectX"
downloads_dir  = os.path.join(resource_dir, "downloads")
paintings_dir  = os.path.join(resource_dir, "paintings")
faces_dir      = os.path.join(resource_dir, "faces")
temp_dir       = os.path.join(resource_dir, "temp")
models_dir     = os.path.join(resource_dir, "models")
predictor_path = os.path.join(models_dir, "predictor.dat")
style_path     = os.path.join(models_dir, "style150.h5")
svm_path       = os.path.join(models_dir, "svm.pkl")
dataset_dir    = os.path.join(models_dir, "dataset")
emotions       = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
emotions_dir   = [os.path.join(dataset_dir, emotion) for emotion in emotions]
