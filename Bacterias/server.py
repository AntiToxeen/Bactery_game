import math
import random
import socket
import psycopg2
import pygame
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from faker import Faker

engine = create_engine("postgresql+psycopg2://postgres:1234@localhost/bacteria")
Session = sessionmaker(engine)
s = Session()

pygame.init()
WIDTH_ROOM, HEIGHT_ROOM = 4000, 4000
WIDTH_SERVER, HEIGHT_SERVER = 300, 300
FPS = 100
fake = Faker()

colors = ['Maroon', 'DarkRed', 'FireBrick', 'Red', 'Salmon', 'Tomato', 'Coral', 'OrangeRed', 'Chocolate', 'SandyBrown',
          'DarkOrange', 'Orange', 'DarkGoldenrod', 'Goldenrod', 'Gold', 'Olive', 'Yellow', 'YellowGreen', 'GreenYellow',
          'Chartreuse', 'LawnGreen', 'Green', 'Lime', 'SpringGreen', 'MediumSpringGreen', 'Turquoise',
          'LightSeaGreen', 'MediumTurquoise', 'Teal', 'DarkCyan', 'Aqua', 'Cyan', 'DeepSkyBlue',
          'DodgerBlue', 'RoyalBlue', 'Navy', 'DarkBlue', 'MediumBlue']

screen = pygame.display.set_mode((WIDTH_SERVER, HEIGHT_SERVER))
pygame.display.set_caption("Серверное окно")
clock = pygame.time.Clock()


def find_vector(data: str):
    first = None
    for index, value in enumerate(data):
        if value == "<":
            first = index
        if value == ">" and first is not None:
            second = index
            vector = data[first + 1:second].split(",")
            vector = list(map(float, vector))
            return vector
    return ""


def find_color(info: str):
    first = None
    for index, value in enumerate(info):
        if value == "<":
            first = index
        if value == ">" and first is not None:
            second = index
            info = info[first + 1:second].split(",")
            return info
    return ""


class Base(DeclarativeBase):
    pass


# Декларативный класс таблицы игроков
class Player(Base):
    __tablename__ = "gamers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250))
    address = Column(String)
    x = Column(Integer, default=500)
    y = Column(Integer, default=500)
    size = Column(Integer, default=75)
    errors = Column(Integer, default=0)
    abs_speed = Column(Integer, default=1)
    speed_x = Column(Integer, default=2)
    speed_y = Column(Integer, default=2)
    color = Column(String(250), default="red")
    w_vision = Column(Integer, default=800)
    h_vision = Column(Integer, default=600)

    def __init__(self, name, address):
        self.name = name
        self.address = address


Base.metadata.create_all(engine)


# Локальный класс игроков
class LocalPlayer:
    def __init__(self, id, name, sock, addr, color):
        self.id = id
        self.db: Player = s.get(Player, self.id)
        self.sock = sock
        self.name = name
        self.address = addr
        self.x = 500
        self.y = 500
        self.size = 75
        self.errors = 0
        self.abs_speed = 1
        self.speed_x = 2
        self.speed_y = 2
        self.color = color
        self.w_vision = 800
        self.h_vision = 600
        self.L = 1

    def update(self):
        if self.x - self.size <= 0:
            if self.speed_x >= 0:
                self.x += self.speed_x
        elif self.x + self.size >= WIDTH_ROOM:
            if self.speed_x <= 0:
                self.x += self.speed_x
        else:
            self.x += self.speed_x

        if self.y - self.size <= 0:
            if self.speed_y >= 0:
                self.y += self.speed_y
        elif self.y + self.size >= HEIGHT_ROOM:
            if self.speed_y <= 0:
                self.y += self.speed_y
        else:
            self.y += self.speed_y
        if self.size > 100:
            self.size = self.size - (self.size / 20000)

        if self.size >= self.w_vision / 4:
            if self.w_vision <= WIDTH_ROOM or self.h_vision <= HEIGHT_ROOM:
                self.L *= 2
                self.w_vision = 800 * self.L
                self.h_vision = 600 * self.L

    def change_speed(self, vector):
        vector = find_vector(vector)
        if vector[0] == 0 and vector[1] == 0:
            self.speed_x = self.speed_y = 0
        else:
            vector = vector[0] * self.abs_speed, vector[1] * self.abs_speed
            self.speed_x = vector[0]
            self.speed_y = vector[1]

    def new_speed(self):
        self.abs_speed = 10 / math.sqrt(self.size)

    def load(self):
        self.size = self.db.size
        self.abs_speed = self.db.abs_speed
        self.speed_x = self.db.speed_x
        self.speed_y = self.db.speed_y
        self.errors = self.db.errors
        self.x = self.db.x
        self.y = self.db.y
        self.color = self.db.color
        self.w_vision = self.db.w_vision
        self.h_vision = self.db.h_vision
        return self

    def sync(self):
        self.db.size = self.size
        self.db.abs_speed = self.abs_speed
        self.db.speed_x = self.speed_x
        self.db.speed_y = self.speed_y
        self.db.errors = self.errors
        self.db.x = self.x
        self.db.y = self.y
        self.db.color = self.color
        self.db.w_vision = self.w_vision
        self.db.h_vision = self.h_vision
        s.merge(self.db)
        s.commit()


class Food:
    def __init__(self, x, y, size, color):
        self.x = x
        self.y = y
        self.size = size
        self.color = color


main_sock = socket.socket(socket.AF_INET,
                          socket.SOCK_STREAM)  # 1) Это семейство адресов IPV4. 2) Транспортный протокол TCP.
main_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Отключаем пакетирование для поддержки FPS.
main_sock.bind(("localhost", 10000))  # Указываем для сокета IP адрес и PORT.
main_sock.setblocking(False)  # Непрерывность, не ждем ответа.
main_sock.listen(5)  # 5 одновременных соединений на обработку
print("Сокет создался")

players = {}

MOBS_QUANTITY = 30
for x in range(MOBS_QUANTITY):
    server_mob = Player(fake.first_name(), None)
    server_mob.color = random.choice(colors)
    server_mob.x, server_mob.y = random.randint(0, WIDTH_ROOM), random.randint(0, HEIGHT_ROOM)
    server_mob.speed_x, server_mob.speed_y = random.randint(-1, 1), random.randint(-1, 1)
    server_mob.size = random.randint(30, 100)
    s.add(server_mob)
    s.commit()
    local_mob = LocalPlayer(server_mob.id, server_mob.name, None, None, server_mob.color).load()
    players[server_mob.id] = local_mob

FOOD_SIZE = 20
FOOD_QUANTITY = WIDTH_ROOM * HEIGHT_ROOM // 40000
foods = []
for x in range(FOOD_QUANTITY):
    foods.append(Food(
        random.randint(0, WIDTH_ROOM),
        random.randint(0, HEIGHT_ROOM),
        FOOD_SIZE,
        random.choice(colors)
    ))

server_works = True
tick = -1
while server_works:
    tick += 1
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            server_works = False
    if tick % 200 == 0:
        try:  # Блок подключения новых игроков.
            new_sock, addr = main_sock.accept()
            new_sock.setblocking(False)
            print("Подключился:", new_sock, addr)
            player = Player("Ameba", addr)
            login = new_sock.recv(1024).decode()
            if login.startswith("color"):
                login = find_color(login[6:])
                player.name, player.color = login
            s.merge(player)
            s.commit()
            addr = f"({addr[0]},{addr[1]})"
            data = s.query(Player).filter(Player.address == addr)
            for user in data:
                player = LocalPlayer(user.id, user.name, new_sock, addr, user.color).load()
                players[user.id] = player
        except BlockingIOError:
            pass
        need = MOBS_QUANTITY - len(players)
        if need > 0:
            for x in range(need):
                server_mob = Player(fake.first_name(), None)
                server_mob.color = random.choice(colors)
                spawn: Food = random.choice(foods)
                server_mob.x, server_mob.y = spawn.x, spawn.y
                foods.remove(spawn)
                server_mob.size = random.randint(30, 100)
                s.add(server_mob)
                s.commit()
                local_mob = LocalPlayer(server_mob.id, server_mob.name, None, None, server_mob.color).load()
                local_mob.new_speed()
                players[server_mob.id] = local_mob
        need = FOOD_QUANTITY - len(foods)
        if need > 0:
            for x in range(need):
                foods.append(Food(
                    random.randint(0, WIDTH_ROOM),
                    random.randint(0, HEIGHT_ROOM),
                    FOOD_SIZE,
                    random.choice(colors)
                ))

    for id in list(players):  # Цикл приема информации от клиентов.
        if players[id].sock is not None:
            try:
                data = players[id].sock.recv(1024).decode()
                # print(data)
                players[id].change_speed(data)
            except:
                pass
        else:
            if tick % 400 == 0:
                vector = f"<{random.randint(-1, 1)},{random.randint(-1, 1)}>"
                players[id].change_speed(vector)
    visible_bacterias = {}
    for id in list(players):
        visible_bacterias[id] = []
    pairs = list(players.items())
    for i in range(0, len(pairs)):
        for food in foods:
            hero: LocalPlayer = pairs[i][1]
            dist_x = food.x - hero.x
            dist_y = food.y - hero.y
            if abs(dist_x) <= hero.w_vision // 2 + food.size and abs(dist_y) <= hero.h_vision // 2 + food.size:
                distance = math.sqrt(dist_x ** 2 + dist_y ** 2)
                if distance < hero.size:
                    hero.size = math.sqrt(hero.size ** 2 + food.size ** 2)
                    hero.new_speed()
                    food.size = 0
                    foods.remove(food)
                if hero.sock is not None:
                    x_ = str(round(dist_x / hero.L))
                    y_ = str(round(dist_y / hero.L))
                    size_ = str(round(food.size / hero.L))
                    color_ = food.color
                    data = f"{x_} {y_} {size_} {color_}"
                    visible_bacterias[hero.id].append(data)

        for j in range(i + 1, len(pairs)):
            hero_1: LocalPlayer = pairs[i][1]
            hero_2: LocalPlayer = pairs[j][1]
            dist_x = hero_2.x - hero_1.x
            dist_y = hero_2.y - hero_1.y
            if abs(dist_x) <= hero_1.w_vision // 2 + hero_2.size and abs(dist_y) <= hero_1.h_vision // 2 + hero_2.size:
                distance = math.sqrt(dist_x ** 2 + dist_y ** 2)
                if distance <= hero_1.size and hero_1.size > hero_2.size * 1.1:
                    hero_1.size = math.sqrt(hero_1.size ** 2 + hero_2.size ** 2)
                    hero_1.new_speed()
                    hero_2.size, hero_2.speed_x, hero_2.speed_y = 0, 0, 0
                if hero_1.sock is not None:
                    x_ = str(round(dist_x / hero_1.L))
                    y_ = str(round(dist_y / hero_1.L))
                    size_ = str(round(hero_2.size / hero_1.L))
                    color_ = hero_2.color
                    name_ = hero_2.name
                    data = f"{x_} {y_} {size_} {color_} {name_}"
                    visible_bacterias[hero_1.id].append(data)
            if abs(dist_x) <= hero_2.w_vision // 2 + hero_1.size and abs(dist_y) <= hero_2.h_vision // 2 + hero_1.size:
                distance = math.sqrt(dist_x ** 2 + dist_y ** 2)
                if distance <= hero_2.size and hero_2.size > hero_1.size * 1.1:
                    hero_2.size = math.sqrt(hero_1.size ** 2 + hero_2.size ** 2)
                    hero_2.new_speed()
                    hero_1.size, hero_1.speed_x, hero_1.speed_y = 0, 0, 0
                if hero_2.sock is not None:
                    x_ = str(round(-dist_x / hero_2.L))
                    y_ = str(round(-dist_y / hero_2.L))
                    size_ = str(round(hero_1.size / hero_2.L))
                    color_ = hero_1.color
                    name_ = hero_1.name
                    data = f"{x_} {y_} {size_} {color_} {name_}"
                    visible_bacterias[hero_2.id].append(data)
    for id in list(players):  # Цикл подготовки информации
        r_ = str(round(players[id].size / players[id].L))
        visible_bacterias[id] = [r_] + visible_bacterias[id]
        visible_bacterias[id] = "<" + ",".join(visible_bacterias[id]) + ">"
    for id in list(players):  # Цикл отправки информации клиентам.
        if players[id].sock is not None:
            try:
                players[id].sock.send(visible_bacterias[id].encode())
            except:
                players[id].errors += 1
    for id in list(players):  # цикл чистки игроков
        if players[id].errors >= 500 or players[id].size == 0:
            if players[id].sock is not None:
                players[id].sock.close()
            del players[id]
            s.query(Player).filter(Player.id == id).delete()
            s.commit()
            print(f"Игрок {id} отключен.")
    screen.fill("black")
    for id in list(players):  # Цикл отрисовки всех бактерий.
        player = players[id]
        x = player.x * WIDTH_SERVER // WIDTH_ROOM
        y = player.y * HEIGHT_SERVER // HEIGHT_ROOM
        size = player.size * WIDTH_SERVER // WIDTH_ROOM
        pygame.draw.circle(screen, player.color, (x, y), size)
    for id in list(players):  # Цикл обновления бактерий
        players[id].update()
        if tick % 300 == 0:
            players[id].sync()
    pygame.display.update()
pygame.quit()
main_sock.close()
s.query(Player).delete()
s.commit()
