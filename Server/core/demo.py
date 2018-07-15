import os
import glob
from tkinter import *

import numpy as np
import cv2
import dlib
from PIL import Image, ImageTk
from sklearn.externals import joblib

from database.modelDB import dataset_dir, emotions, ModelDatabaseHandler
from core import detector
from database.paintingDB import get_all_landmarks, faces_dir, svm_dir
from core.comparator import Comparator


class GUI(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)

        width, height = 720, 765
        master.minsize(width, height)
        master.maxsize(width, height)
        self.pack()

        self.camera_label = Label()
        self.camera_label.pack()
        self.camera_label.place(x=0, y=0)

        self.dataset_label = Label()
        self.dataset_label.pack()
        self.dataset_label.place(x=0, y=405)

        self.painting_label = Label()
        self.painting_label.pack()
        self.painting_label.place(x=360, y=405)

        self.emotion_text = StringVar()
        self.emotion_label = Label(textvariable=self.emotion_text, font=("Helvetica", 30))
        self.emotion_label.pack()
        self.emotion_label.place(x=10, y=10)

        self.video_capture = cv2.VideoCapture(0)
        self.tracker = dlib.correlation_tracker()
        self.bounding_box = None
        self.camera_image = None

        self.svm = joblib.load(svm_dir)

        dataset = ModelDatabaseHandler().get_landmarks("Total")
        dataset_landmarks = [[] for _ in range(len(emotions))]
        self.dataset_map = [[] for _ in range(len(emotions))]
        for lid, eid, points, _ in dataset:
            self.dataset_map[eid].append(lid - 1)
            dataset_landmarks[eid].append(points)
        self.dataset_comparators = [Comparator(points, 1) for points in dataset_landmarks]
        self.dataset_face_image = None
        self.dataset_faces = []
        for img_file in sorted(glob.glob(os.path.join(dataset_dir, "total/*.jpg"))):
            self.dataset_faces.append(Image.open(img_file))

        paintings = get_all_landmarks()
        painting_landmarks = [[] for _ in range(len(emotions))]
        self.painting_map = [[] for _ in range(len(emotions))]
        for lid, _, eid, _, points, _ in paintings:
            self.painting_map[eid].append(lid - 1)
            painting_landmarks[eid].append(points)
        self.painting_comparators = [Comparator(points, 1) for points in painting_landmarks]
        self.painting_face_image = None
        self.painting_faces = []
        for img_file in sorted(glob.glob(os.path.join(faces_dir, "*.jpg"))):
            self.painting_faces.append(Image.open(img_file))

        self.after(0, self.refresh)

    def refresh(self):
        try:
            _, frame = self.video_capture.read()
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.flip(frame, 1)

            if self.bounding_box:
                self.track(frame)
                if not self.bounding_box:
                    self.detect(frame)
            else:
                self.detect(frame)

            if self.bounding_box:
                # draw rectangle around face
                left, top, right, bottom = detector.rect_to_list(self.bounding_box)
                cv2.rectangle(frame, (left, top), (right, bottom), (255, 255, 0), 2)

                # draw red dots for landmarks
                landmarks = detector.detect_landmarks(frame, self.bounding_box)
                normalized = detector.normalize_landmarks(landmarks)
                posed = detector.pose_landmarks(landmarks)
                for x, y in landmarks:
                    cv2.circle(frame, (int(x), int(y)), 4, (255, 0, 0), -1)

                emotion_id = self.svm.predict([posed])[0]
                self.emotion_text.set(emotions[emotion_id])

                face_id = self.dataset_comparators[emotion_id](normalized)[0]
                face_id = self.dataset_map[emotion_id][face_id]
                face = self.dataset_faces[face_id]
                face = face.resize([360, 360])
                self.dataset_face_image = ImageTk.PhotoImage(image=face)
                self.dataset_label.configure(image=self.dataset_face_image)
                self.dataset_label.image = self.dataset_face_image

                face_id = self.painting_comparators[emotion_id](normalized)[0]
                face_id = self.painting_map[emotion_id][face_id]
                face = self.painting_faces[face_id]
                face = face.resize([360, 360])
                self.painting_face_image = ImageTk.PhotoImage(image=face)
                self.painting_label.configure(image=self.painting_face_image)
                self.painting_label.image = self.painting_face_image

            frame = Image.fromarray(frame)
            frame = frame.resize([720, 405])
            self.camera_image = ImageTk.PhotoImage(image=frame)
            self.camera_label.configure(image=self.camera_image)
            self.camera_label.image = self.camera_image

            self.after(1, self.refresh)

        except KeyboardInterrupt:
            pass

    def detect(self, frame):
        faces = detector.detect_face(frame)
        if faces:
            area = [bbox.area() for bbox in faces]
            self.bounding_box = faces[np.argmax(area)]
            self.tracker.start_track(frame, self.bounding_box)

    def track(self, frame):
        confidence = self.tracker.update(frame)
        if confidence > 8:
            left, top, right, bottom = detector.rect_to_list(self.tracker.get_position())
            self.bounding_box = detector.create_rect(int(left), int(top), int(right), int(bottom))
        else:
            self.bounding_box = None


if __name__ == "__main__":
    root = Tk()
    root.title("Emotion Analysis")
    gui = GUI(root)
    gui.mainloop()
