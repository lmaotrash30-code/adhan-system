import datetime
import time
import pygame

pygame.init()
pygame.mixer.init()


while True:
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M:%S")

    print(current_time)

    if current_time.startswith("11:53"):
        print("Triggering Adhan!")

        pygame.mixer.music.load("adhan.mp3")
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(1)

    time.sleep(1)