from tkinter import *
import cv2
from PIL import Image, ImageTk
from core.detector import detect_face, detect_landmarks, create_rect, break_rect
import numpy as np
import dlib
from dev.testingDB import get_landmarks, dataset_dir
from core.comparator import Comparator
import os
import glob


class GUI(Frame):
    def __init__(self, master, directory=os.path.join(dataset_dir, "total")):
        Frame.__init__(self, master)

        width, height = 1000, 360
        master.minsize(width, height)
        master.maxsize(width, height)
        self.pack()

        self.camera_label = Label()
        self.camera_label.pack()
        self.camera_label.place(x=0, y=0)

        self.face_label = Label()
        self.face_label.pack()
        self.face_label.place(x=640, y=0)

        self.video_capture = cv2.VideoCapture(0)
        self.tracker = dlib.correlation_tracker()
        self.bounding_box = None
        self.camera_image = None

        landmarks = get_landmarks("Total")
        self.emotions = [row[1] for row in landmarks]
        self.comparator = Comparator(np.array([row[2] for row in landmarks]), 1)
        self.face_image = None
        self.faces = []
        for img_file in sorted(glob.glob(os.path.join(directory, "*.jpg"))):
            self.faces.append(Image.open(img_file))

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
                left, top, right, bottom = break_rect(self.bounding_box)
                cv2.rectangle(frame, (left, top), (right, bottom), (255, 255, 0), 2)

                # draw red dots for landmarks
                landmarks, normalized = detect_landmarks(frame, self.bounding_box)
                for point in landmarks:
                    cv2.circle(frame, (int(point[0]), int(point[1])), 4, (255, 0, 0), -1)

                face = self.faces[self.comparator(normalized)[0]]
                face = face.resize([360, 360])
                self.face_image = ImageTk.PhotoImage(image=face)
                self.face_label.configure(image=self.face_image)
                self.face_label.image = self.face_image

            frame = Image.fromarray(frame)
            frame = frame.resize([640, 360])
            self.camera_image = ImageTk.PhotoImage(image=frame)
            self.camera_label.configure(image=self.camera_image)
            self.camera_label.image = self.camera_image

            self.after(1, self.refresh)

        except KeyboardInterrupt:
            pass

    def detect(self, frame):
        faces = detect_face(frame)
        if faces:
            area = [bbox.area() for bbox in faces]
            self.bounding_box = faces[np.argmax(area)]
            self.tracker.start_track(frame, self.bounding_box)

    def track(self, frame):
        confidence = self.tracker.update(frame)
        if confidence > 8:
            left, top, right, bottom = break_rect(self.tracker.get_position())
            self.bounding_box = create_rect(int(left), int(top), int(right), int(bottom))
        else:
            self.bounding_box = None


if __name__ == "__main__":
    root = Tk()
    root.title("Emotion Analysis")
    gui = GUI(root)
    gui.mainloop()
