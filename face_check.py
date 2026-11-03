# Eslatma: bu faqat rasmda yuzga o‘xshash obyekt borligini taxmin qiladi.
# Shaxsni aniqlamaydi va yoshni tasdiqlamaydi.
import cv2
import numpy as np

def contains_face(image_bytes: bytes) -> bool:
    arr=np.frombuffer(image_bytes, dtype=np.uint8)
    img=cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None: return False
    gray=cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces=cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60,60))
    return len(faces) > 0
