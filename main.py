
from ctypes import sizeof
import json
from re import T, X
import sys
import pygame
import random
import os

#global vars
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WIDTH = 20*40
HEIGHT = 16*40
FPS = 60
MAP_BLOCK_SIZE = 40

#init
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("demo")
clock = pygame.time.Clock()
running = True

#解析获取地图背景+元素矩阵

wall_group = pygame.sprite.Group()
bg_group = pygame.sprite.Group()
hero_group = pygame.sprite.Group()
bomb_group = pygame.sprite.Group()

def loadImgByPath(path):
    return pygame.image.load(path).convert_alpha()

def praseJsonObj(jsonPath):
    with open(jsonPath, 'r', encoding='utf8') as fp:
        json_data = json.load(fp)
    return json_data

#定义战斗区域每个像素点上的元素
def battleMapInitBuild(mapBgList, mapWallList):
    pass

#全局元素刷新
def globalDrawScreen(screen, map, mapBgList, mapWallList, hero_group):

    for y in range(map.height):
        for x in range(map.width):
            mapBgList[y][x].draw(screen)

    for y in range(map.height):
        for x in range(map.width):
            for hero in hero_group.sprites():  
                hero.draw(screen)
            for bomb in bomb_group.sprites():  
                bomb.draw(screen)         
            if mapWallList[y][x] not in ["0", "x"]:
                mapWallList[y][x].draw(screen)
            

#解析图片
class MapParse():
    def __init__(self, jsonPath, mapId, **kwargs):
        self.data = self.__parseJsonData(jsonPath)
        self.mapType = self.data['mapType']
        self.mapNameCN = self.data['mapNameCN']
        self.mapElemPath = self.data['mapElemPath']
        self.mapBgList = self.data['mapBgArray']
        self.elementList = self.data['mapElements']

        #根据传入的地图ID解析地图
        self.offSet = 50
        self.map = self.__praseMap(self.data['mapList'], mapId)
        self.mapList = self.map['mapElementArray']
        self.mapName = self.map['name']
        self.blockSize = self.map['mapBgBlockSize']
        self.height = self.map['mapY']
        self.width = self.map['mapX']
        self.screen_size = (self.map['mapWidth'] + self.offSet, self.map['mapHeight'] + self.offSet)

    def __parseJsonData(self, jsonPath):
        with open(jsonPath, 'r', encoding='utf8')as fp:
            json_data = json.load(fp)
        return json_data

    def __praseMap(self, mapList, mapId):
        for i in range(len(mapList)):
            map = json.loads(json.dumps(mapList[i]))
            if map['name'] == mapId:
                return map

    def getMapElement(self, elementId):
        for i in range(len(self.elementList)):
            elem = json.loads(json.dumps(self.elementList[i]))
            if elem['id'] == elementId:
                return elem

    def getBgList(self):
        bgList = []
        for y in range(self.height):
            bgListX = []
            for x in range(self.width):
                instance = self.getMapElement(int(self.mapBgList[y][x]))
                bg = Background(str(self.mapElemPath + instance['name']), [x,y], self.blockSize, instance, self.offSet)
                bg_group.add(bg)
                bgListX.append(bg)
            bgList.append(bgListX)
        return bgList
    
    def getWallList(self):
        wallList = []
        for y in range(self.height):
            wallListX = []
            for x in range(self.width):
                if self.mapList[y][x] in ["0", "x"]:
                    wallListX.append(self.mapList[y][x])
                else:
                    instance = self.getMapElement(int(self.mapList[y][x]))
                    elem = Wall(str(self.mapElemPath + instance['name']), [x,y], self.blockSize, instance, self.offSet)
                    wall_group.add(elem)
                    wallListX.append(elem)
            wallList.append(wallListX)
        return wallList

class Hero(pygame.sprite.Sprite):
    def __init__(self, jsonPath, coordinate, blocksize, mapParser, mapWallList, **kwargs):
        pygame.sprite.Sprite.__init__(self)
        self.hero = self.__praseHero(jsonPath)
        self.mapParser = mapParser
        self.wallList = mapWallList
        self.image = pygame.image.load(self.hero['elemPath']+self.hero['down']['stand']).convert_alpha()
        self.rect = self.image.get_rect()
        self.coordinate = coordinate
        self.blocksize = blocksize
        self.offSet = mapParser.offSet
        self.rect.bottom = ((coordinate[1]+1) * blocksize) + self.offSet
        self.rect.centerx = (coordinate[0] * blocksize) + (blocksize/2) + self.offSet

        #角色属性
        self.id = self.hero['id']
        self.boomPower = self.hero['boomPower']
        self.boomNum = self.hero['boomNum']
        self.speed = self.hero['speed']
        self.giftType = self.hero['giftType']
        self.dead = False

        #角色动画效果属性
        self.upAminationList = self.__getAminationList("up")
        self.downAminationList = self.__getAminationList("down")
        self.rightAminationList = self.__getAminationList("right")
        self.leftAminationList = self.__getAminationList("left")
        self.leftLastUpdateTime = pygame.time.get_ticks()
        self.rightLastUpdateTime = pygame.time.get_ticks()
        self.upLastUpdateTime = pygame.time.get_ticks()
        self.downLastUpdateTime = pygame.time.get_ticks()
        self.leftFrame = 0
        self.rightFrame = 0
        self.upFrame = 0
        self.downFrame = 0
        self.leftStandImg = pygame.image.load(self.hero['elemPath']+self.hero["left"]['stand'])
        self.rightStandImg = pygame.image.load(self.hero['elemPath']+self.hero["right"]['stand'])
        self.upStandImg = pygame.image.load(self.hero['elemPath']+self.hero["up"]['stand'])
        self.downStandImg = pygame.image.load(self.hero['elemPath']+self.hero["down"]['stand'])
        self.rightFrameRate = self.hero["right"]["animationDelay"]
        self.leftFrameRate = self.hero["left"]["animationDelay"]
        self.upFrameRate = self.hero["up"]["animationDelay"]
        self.downFrameRate = self.hero["down"]["animationDelay"]

        #角色持有炸弹属性
        self.bombConfig = None
        self.bombType = None
        self.bombImgList = None

    def __getAminationList(self, direction):
        dict = self.hero[direction]
        aminationList = []
        for pic in range(len(dict["animationList"])):
            image = pygame.image.load(self.hero['elemPath']+dict["animationList"][pic])
            aminationList.append(image)
        return aminationList


    def __praseHero(self, jsonPath):
        with open(jsonPath, 'r', encoding='utf8')as fp:
            json_data = json.load(fp)
        return json_data

    def __updateImage(self, direction):
        now = pygame.time.get_ticks()
        if direction == "left":
            if now - self.leftLastUpdateTime > self.leftFrameRate:
                self.leftLastUpdateTime = now
                self.leftFrame += 1
                if self.leftFrame == self.hero["left"]["animationFrames"]:
                    self.leftFrame = 0
                self.image = self.leftAminationList[self.leftFrame]
        if direction == "right":
            if now - self.rightLastUpdateTime > self.rightFrameRate:
                self.rightLastUpdateTime = now
                self.rightFrame += 1
                if self.rightFrame == self.hero["right"]["animationFrames"]:
                    self.rightFrame = 0
                self.image = self.rightAminationList[self.rightFrame]
        if direction == "up":
            if now - self.upLastUpdateTime > self.upFrameRate:
                self.upLastUpdateTime = now
                self.upFrame += 1
                if self.upFrame == self.hero["up"]["animationFrames"]:
                    self.upFrame = 0
                self.image = self.upAminationList[self.upFrame]
        if direction == "down":
            if now - self.downLastUpdateTime > self.downFrameRate:
                self.downLastUpdateTime = now
                self.downFrame += 1
                if self.downFrame == self.hero["down"]["animationFrames"]:
                    self.downFrame = 0
                self.image = self.downAminationList[self.downFrame]

    #人物绑定炸弹
    def updateBomb(self, bombConfig, bombType, bombImgList):
        self.bombConfig = bombConfig
        self.bombType = bombType
        self.bombImgList = bombImgList

    def updateImageKeyUp(self, direction):
        if direction == "left":
            self.image = self.leftStandImg
        if direction == "right":
            self.image = self.rightStandImg
        if direction == "up":
            self.image = self.upStandImg
        if direction == "down":
            self.image = self.downStandImg

    def getCenterCoordinate(self):
        #角色中心位置
        self.pixelX = self.rect.centerx
        self.pixelY = (self.rect.bottom - (self.blocksize/2))
        curCoordinate = [int((self.pixelX - self.offSet)/self.blocksize), int((self.pixelY - self.offSet)/self.blocksize)]
        self.coordinate = curCoordinate
        return curCoordinate
    
    def getCenterPixel(self):
        return[int(self.rect.centerx), int((self.rect.bottom - (self.blocksize/2)))]

    def move(self, direction):
        self.__updateImage(direction)
        heroCoordinate = self.getCenterCoordinate()
        heroCenterPixel = self.getCenterPixel()


        if direction == "right":
            
            if heroCoordinate[0] < self.mapParser.width - 1:
                heroCoordinate[0] += 1
            rightWall = self.wallList[heroCoordinate[1]][heroCoordinate[0]]
            if rightWall != "0" and rightWall != "x":
                wallCenterPixel = rightWall.getCenterPixel()
                yShift = wallCenterPixel[1]-heroCenterPixel[1]

                if wallCenterPixel[0]-heroCenterPixel[0] > self.blocksize:
                    self.rect.x += self.speed
                if rightWall.element['rightThroughAble'] == 1:
                    self.rect.x += self.speed
            elif rightWall == "x":
                pass
            else:
                self.rect.x += self.speed

        if direction == "left":
            
            if heroCoordinate[0] > 0:
                heroCoordinate[0] -= 1
            leftWall = self.wallList[heroCoordinate[1]][heroCoordinate[0]]
            if leftWall != "0" and leftWall != "x":
                wallCenterPixel = leftWall.getCenterPixel()
                yShift = wallCenterPixel[1]-heroCenterPixel[1]

                if heroCenterPixel[0]-wallCenterPixel[0] > self.blocksize:
                    self.rect.x -= self.speed
                if leftWall.element['leftThroughAble'] == 1:
                    self.rect.x -= self.speed
            elif leftWall == "x":
                pass
            else:
                self.rect.x -= self.speed
            
        if direction == "up":
            if heroCoordinate[1] > 0:
                heroCoordinate[1] -= 1
            upWall = self.wallList[heroCoordinate[1]][heroCoordinate[0]]
            if upWall != "0" and upWall != "x":

                wallCenterPixel = upWall.getCenterPixel()
                xShift = wallCenterPixel[0]-heroCenterPixel[0]

                if heroCenterPixel[1]-wallCenterPixel[1] > self.blocksize:
                    self.rect.y -= self.speed
                if upWall.element['bottomThroughAble'] == 1:
                    self.rect.y -= self.speed
            elif upWall == "x":
                pass
            else:
                self.rect.y -= self.speed

        if direction == "down":

            if heroCoordinate[1] < self.mapParser.height-1:
                heroCoordinate[1] += 1
            bottomWall = self.wallList[heroCoordinate[1]][heroCoordinate[0]]
            if bottomWall != "0" and bottomWall != "x":
                wallCenterPixel = bottomWall.getCenterPixel()
                xShift = wallCenterPixel[0]-heroCenterPixel[0]

                if wallCenterPixel[1]-heroCenterPixel[1] > self.blocksize:
                    self.rect.y += self.speed
                if bottomWall.element['topThroughAble'] == 1:
                    self.rect.y += self.speed
            elif bottomWall == "x":
                pass
            else:
                self.rect.y += self.speed
            


        #边界检测
        if self.rect.centerx > ((self.mapParser.width-1) * self.blocksize) + (self.blocksize/2) + self.offSet:
            self.rect.centerx = ((self.mapParser.width-1) * self.blocksize) + (self.blocksize/2) + self.offSet
        if self.rect.centerx < (self.blocksize/2) + self.offSet:
            self.rect.centerx = (self.blocksize/2) + self.offSet
        if self.rect.bottom > self.mapParser.height * self.blocksize + self.offSet:
            self.rect.bottom = self.mapParser.height * self.blocksize + self.offSet
        if self.rect.bottom < self.offSet + self.blocksize:
            self.rect.bottom = self.offSet + self.blocksize

        return True
    
    def draw(self, screen):
        screen.blit(self.image, self.rect)
        return True

    def dropBomb(self):
        bomb = Bomb(self.bombConfig, self.bombType, self.bombImgList, self.getCenterCoordinate(), self.blocksize, 1, self.offSet)
        bomb_group.add(bomb)
    
    def updata(self):
        if not(self.dead):
            #获取键盘按键
            key_pressed = pygame.key.get_pressed()
            if key_pressed[pygame.K_RIGHT]:
                self.move("right")
            if key_pressed[pygame.K_LEFT]:
                self.move("left")
            if key_pressed[pygame.K_UP]:
                self.move("up")
            if key_pressed[pygame.K_DOWN]:
                self.move("down")
            if key_pressed[pygame.K_SPACE]:
                hero.dropBomb()
            

class Bomb(pygame.sprite.Sprite):
    def __init__(self, bombConfig, bombType, bombImgList, coordinate, blocksize, element, mapoffSet, **kwargs):
        pygame.sprite.Sprite.__init__(self)
        self.bombConfig = bombConfig
        self.bombType = bombType
        self.bombImgList = bombImgList
        self.image = self.bombImgList[0]
        self.rect = self.image.get_rect()
        self.element = element
        self.offSet = mapoffSet
        self.coordinate = coordinate
        self.blocksize = blocksize
        self.rect.bottom = ((coordinate[1]+1) * blocksize) + self.offSet
        self.rect.centerx = (coordinate[0] * blocksize) + (blocksize/2) + self.offSet

    #绘制到屏幕上
    def draw(self, screen):
        screen.blit(self.image, self.rect)
        return True



class Wall(pygame.sprite.Sprite):
    def __init__(self, imagePath, coordinate, blocksize, element, mapoffSet, **kwargs):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load(imagePath).convert_alpha()
        self.rect = self.image.get_rect()
        self.element = element
        self.rect.centerx = ((element['xBlocks']*blocksize)/2) + (coordinate[0]*blocksize) + mapoffSet
        self.rect.centerx -= element['xOffset']
        self.rect.bottom = ((element['yBlocks'] + coordinate[1]) * blocksize) + mapoffSet
        self.rect.bottom += element['yOffset']
        self.coordinate = coordinate
        self.blocksize = blocksize
        self.mapoffSet = mapoffSet


    #绘制到屏幕上
    def draw(self, screen):
        screen.blit(self.image, self.rect)
        return True

    def getCenterPixel(self):
        return [int((self.blocksize*self.coordinate[0] + int((self.blocksize/2)) + self.mapoffSet)), int((self.blocksize*self.coordinate[1] + int((self.blocksize/2)) + self.mapoffSet))]

class Background(pygame.sprite.Sprite):
    def __init__(self, imagePath, coordinate, blocksize, element, mapoffSet, **kwargs):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load(imagePath).convert_alpha()
        self.element = element
        self.rect = self.image.get_rect()
        self.rect.left, self.rect.top = (coordinate[0] * blocksize) + mapoffSet, (coordinate[1] * blocksize) + mapoffSet
        self.coordinate = coordinate
        self.blocksize = blocksize

    #绘制到屏幕上
    def draw(self, screen):
        screen.blit(self.image, self.rect)
        return True


map = MapParse("maps/water/water2.json", "water_11")
mapBgList = map.getBgList()
mapWallList = map.getWallList()
battleMap = []
battleMapInitBuild(mapBgList, mapWallList)

#初始化炸弹
bombConfig = praseJsonObj("object/bomb/bomb_config.json")
bombType = praseJsonObj("object/bomb/bomb_257.json")
bombImgList = []
print(bombConfig['bombPath'])
for imgPath in range(len(bombType['aminationList'])):
    img = loadImgByPath(bombConfig['bombPath']+bombType['aminationList'][imgPath])
    bombImgList.append(img)

#创建人物并定义初始位置
hero = Hero("object/body/panda.json", [2,3], 40, map, mapWallList)
hero.updateBomb(bombConfig, bombType, bombImgList)
hero_group.add(hero)


while running:
    time = clock.tick(FPS)
    screen.fill(BLACK)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    globalDrawScreen(screen, map, mapBgList, mapWallList, hero_group)
    hero.updata()


    pygame.display.update()


pygame.quit()