import cv2
import pygame
import numpy as np


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 500
FPS = 10


pygame.init()
pygame.joystick.init()

#  Init webcam.
vid = cv2.VideoCapture(0)

#create game window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Joysticks")

#define font
font_size = 30
font = pygame.font.SysFont("Futura", font_size)

#function for outputting text onto the screen
def draw_text(text, font, text_col, x, y):
    img = font.render(text, True, text_col)
    screen.blit(img, (x, y))
  

#create clock for setting game frame rate
# clock = pygame.time.Clock()

#create empty list to store joysticks
joysticks = []

#  Create player rectangle.
# x = 350
# y = 200
# player = pygame.Rect(x, y, 100, 100)

#define player colour
col = "royalblue"

horiz_move = 0
vert_move = 0

#game loop
run = True

while run:

    #  Draw player.
    # player.topleft = (x, y)
    # pygame.draw.rect(screen, pygame.Color(col), player)

    # for joystick in joysticks:
    #     #  Player movement with analogue sticks.
    #     horiz_move = joystick.get_axis(0)
    #     vert_move = joystick.get_axis(1)

    #     img = font.render(str(joystick.get_axis(0)), True, pygame.Color("azure"))
    #     screen.blit(img, (10, 10))
    #     # draw_text(f"X: {horiz_move:.2f}", font, pygame.Color("azure"), 10, 10)
    #     # draw_text(f"Y: {y:.2f}", font, pygame.Color("azure"), 10, 30)

    #     # if abs(vert_move) > 0.05:
    #     #     y += vert_move * 5
    #     # if abs(horiz_move) > 0.05:
    #     #     x += horiz_move * 5

    #  Еvent handler.
    for event in pygame.event.get():
        if event.type == pygame.JOYDEVICEADDED:
            joy = pygame.joystick.Joystick(event.device_index)
            joysticks.append(joy)
        #  Quit program.
        if event.type == pygame.QUIT:
            run = False
        #  Update display.
        pygame.display.update()

    _, frame = vid.read()
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.rot90(frame)
    frame = pygame.surfarray.make_surface(frame)
    screen.blit(frame, (0, 0))
     
    #  Update background.
    # screen.fill(pygame.Color("midnightblue"))
    # img = font.render(str(joysticks[0].get_axis(0)), True, pygame.Color("azure"))
    # screen.blit(img, (10, 10))

    # clock.tick(FPS)

vid.release() 
pygame.quit()
