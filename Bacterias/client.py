import socket
import pygame
import math
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox


def draw_text(x, y, r, text):
    font = pygame.font.Font(None, r // 2)
    txt = font.render(text, True, "black")
    rect = txt.get_rect(center=(x, y))
    screen.blit(txt, rect)


def find_info(info: str):
    global buffer
    first = None
    for index, value in enumerate(info):
        if value == "<":
            first = index
        if value == ">" and first is not None:
            second = index
            info = info[first+1:second]
            return info
    if buffer < 10000000:
        buffer = int(buffer * 1.5)
    return ""


def draw_bacterias(data: list[str]):
    for num, bact in enumerate(data):
        data = bact.split()
        x = CENTER[0] + int(data[0])
        y = CENTER[1] + int(data[1])
        size = int(data[2])
        color = data[3]
        pygame.draw.circle(screen,color,(x,y),size)
        if len(data) > 4:
            draw_text(x,y,size, data[4])


def scroll(event):
    global color
    color = combo.get()
    style.configure("TCombobox",fieldbackground=color,background="white")


def login():
    global name
    name = row.get()
    if name and color and color in colors:
        root.destroy()
        root.quit()
    else:
        tk.messagebox.showerror('ERROR',"Не выбрано имя или цвет.")


name = ""
color = ""
buffer = 1024
colors = ['Maroon', 'DarkRed', 'FireBrick', 'Red', 'Salmon', 'Tomato', 'Coral', 'OrangeRed', 'Chocolate', 'SandyBrown',
          'DarkOrange', 'Orange', 'DarkGoldenrod', 'Goldenrod', 'Gold', 'Olive', 'Yellow', 'YellowGreen', 'GreenYellow',
          'Chartreuse', 'LawnGreen', 'Green', 'Lime', 'SpringGreen', 'MediumSpringGreen', 'Turquoise',
          'LightSeaGreen', 'MediumTurquoise', 'Teal', 'DarkCyan', 'Aqua', 'Cyan', 'DeepSkyBlue',
          'DodgerBlue', 'RoyalBlue', 'Navy', 'DarkBlue', 'MediumBlue']

root = tk.Tk()
root.title("Логин")
root.geometry("300x200")

style = ttk.Style()
style.theme_use('clam')

name_label = tk.Label(root, text="Введи свой никнейм:")
name_label.pack()

row = tk.Entry(root, width=30, justify="center")
row.pack()

color_label = tk.Label(root, text="Выбери цвет:")
color_label.pack()

combo = ttk.Combobox(root, values=colors, textvariable=color)
combo.bind("<<ComboboxSelected>>", scroll)
combo.pack()

name_btn = tk.Button(root, text="Зайти в игру", command=login)
name_btn.pack()

root.mainloop()

cl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cl_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Отключаем пакетирование для поддержки FPS.
cl_sock.connect(("localhost", 10000))  # Указываем для подключения IP адрес и PORT.
cl_sock.send(f"color:<{name},{color}>".encode())

pygame.init()

WIDTH = 800
HEIGHT = 600
CENTER = (WIDTH // 2, HEIGHT // 2)
old = (0, 0)
radius = 75

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bacterias")


class Grid:
    def __init__(self, screen, color):
        self.screen = screen
        self.color = color
        self.x = 0
        self.y = 0
        self.start_size = 200
        self.size = self.start_size


client_works = True
while client_works:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            client_works = False
        if pygame.mouse.get_focused():
            pos = pygame.mouse.get_pos()
            vector = pos[0] - CENTER[0], pos[1] - CENTER[1]
            lenv = math.sqrt(vector[0] ** 2 + vector[1] ** 2)
            vector = vector[0] / lenv, vector[1] / lenv
            if lenv <= radius:
                vector = (0, 0)
            if vector != old:
                old = vector
                msg = f"<{vector[0]},{vector[1]}>"
                cl_sock.send(msg.encode())
    data = cl_sock.recv(buffer).decode()
    # print(data)
    print(buffer)
    data = find_info(data).split(",")
    screen.fill("grey")
    if data != [""]:
        radius = int(data[0])
        draw_bacterias(data[1:])
    pygame.draw.circle(screen, color, CENTER, radius)
    draw_text(CENTER[0], CENTER[1], radius, name)
    pygame.display.update()
pygame.quit()
