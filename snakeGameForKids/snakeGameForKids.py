import pygame
import random

# Initialize Pygame
pygame.init()

# Define colors
white = (255, 255, 255)
yellow = (255, 255, 102)
black = (0, 0, 0)
red = (213, 50, 80)
green = (0, 255, 0)
blue = (50, 153, 213)

# Set the dimensions of the game window
dis_width = 800
dis_height = 600

# Create the display
dis = pygame.display.set_mode((dis_width, dis_height))
pygame.display.set_caption('Snake Game for my children')

# Set the snake block size and speed
snake_block = 20
snake_speed = 10

# Rainbow color palette
rainbow_colors = [
    (255, 0, 127),  # Pink
    (255, 255, 0),  # Yellow
    (144, 238, 144),  # Light Green
    # Add more colors as desired
]

# Function to draw the snake
def our_snake(snake_block, snake_list):
    for i, x in enumerate(snake_list):
        color = rainbow_colors[i % len(rainbow_colors)]  # Cycle through the rainbow colors
        pygame.draw.rect(dis, color, [x[0], x[1], snake_block, snake_block])

# Main game loop
def gameLoop():
    global  snake_speed # Add this line to declare snake_speed as non-local
    game_over = False
    game_close = False

    # Starting position of the snake
    x1 = dis_width / 2
    y1 = dis_height / 2

    # When the snake moves
    x1_change = 0
    y1_change = 0

    # Define the snake length and list
    snake_List = []
    Length_of_snake = 1

    # Location of the food
    foodx = round(random.randrange(0, dis_width - snake_block) / snake_block) * snake_block
    foody = round(random.randrange(0, dis_height - snake_block) / snake_block) * snake_block

    # Game loop
    while not game_over:
        while game_close == True:
            dis.fill(blue)
            font_style = pygame.font.SysFont(None, 50)
            mesg = font_style.render("You Lost! Press (P)lay Again or (Q)uit", True, red)
            dis.blit(mesg, [dis_width / 6, dis_height / 3])

            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        game_over = True
                        game_close = False
                    if event.key == pygame.K_p:
                        gameLoop()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    x1_change = -snake_block
                    y1_change = 0
                elif event.key == pygame.K_RIGHT:
                    x1_change = snake_block
                    y1_change = 0
                elif event.key == pygame.K_UP:
                    y1_change = -snake_block
                    x1_change = 0
                elif event.key == pygame.K_DOWN:
                    y1_change = snake_block
                    x1_change = 0
                elif event.key == pygame.K_SPACE:  # Press space for double speed
                    snake_speed = snake_speed * 2
                elif event.key == pygame.K_RETURN:  # Press enter to pause
                    pause = True
                    while pause:
                        for event in pygame.event.get():
                            if event.type == pygame.KEYDOWN:
                                if event.key == pygame.K_RETURN:
                                    pause = False

        # Check for boundary collision
        if x1 >= dis_width:
            x1 = 0
        elif x1 < 0:
            x1 = dis_width
        if y1 >= dis_height:
            y1 = 0
        elif y1 < 0:
            y1 = dis_height

        # Move the snake
        x1 += x1_change
        y1 += y1_change
        dis.fill(blue)
        pygame.draw.rect(dis, green, [foodx, foody, snake_block, snake_block])
        snake_Head = []
        snake_Head.append(x1)
        snake_Head.append(y1)
        snake_List.append(snake_Head)
        if len(snake_List) > Length_of_snake:
            del snake_List[0]

        for x in snake_List[:-1]:
            if x == snake_Head:
                game_close = True

        our_snake(snake_block, snake_List)
        pygame.display.update()

        # Snake eating food
        if x1 == foodx and y1 == foody:
            foodx = round(random.randrange(0, dis_width - snake_block) / snake_block) * snake_block
            foody = round(random.randrange(0, dis_height - snake_block) / snake_block) * snake_block
            Length_of_snake += 1
            snake_speed = 15  # Reset speed after eating

        pygame.time.Clock().tick(snake_speed)

    pygame.quit()
    quit()

# Start the game
gameLoop()
