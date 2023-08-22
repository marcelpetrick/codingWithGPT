import argparse
from PIL import Image, ImageDraw, ImageFont
import random


def generate_iterative_random_maze(width, height, wall_thickness):
    DIRECTIONS = [
        (0, -2),  # Up
        (2, 0),  # Right
        (0, 2),  # Down
        (-2, 0)  # Left
    ]
    maze = [[1 for _ in range(2 * height + 1)] for _ in range(2 * width + 1)]
    for x in range(0, 2 * width + 1, wall_thickness):
        for y in range(0, 2 * height + 1, wall_thickness):
            maze[x][y] = 0
    start_x = random.choice(range(1, 2 * width, 2))
    start_y = random.choice(range(1, 2 * height, 2))
    maze[start_x][start_y] = 0

    # Using a stack for iterative implementation
    stack = [(start_x, start_y)]

    while stack:
        x, y = stack[-1]
        random.shuffle(DIRECTIONS)

        # Check for available neighbors
        available_directions = []
        for dx, dy in DIRECTIONS:
            next_x, next_y = x + dx, y + dy
            if 0 < next_x < 2 * width and 0 < next_y < 2 * height and maze[next_x][next_y] == 1:
                available_directions.append((dx, dy))

        if available_directions:
            dx, dy = random.choice(available_directions)
            next_x, next_y = x + dx, y + dy
            maze[next_x][next_y] = 0
            maze[x + dx // 2][y + dy // 2] = 0
            stack.append((next_x, next_y))
        else:
            # No available neighbors, backtrack
            stack.pop()

    for _ in range((width * height) // 5):
        x = random.choice(range(1, 2 * width, 2))
        y = random.choice(range(1, 2 * height, 2))
        direction = random.choice(DIRECTIONS)
        if 0 < x + direction[0] < 2 * width and 0 < y + direction[1] < 2 * height:
            maze[x + direction[0] // 2][y + direction[1] // 2] = 0

    return maze




# Updated drawing function
def draw_updated_labyrinth(labyrinth, wall_thickness):
    width = len(labyrinth)
    height = len(labyrinth[0])
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    for i in range(width):
        for j in range(height):
            if labyrinth[i][j] == 1:
                draw.point((i, j), fill='black')
    goal = "A"
    font = ImageFont.load_default()
    text_width, text_height = font.getsize(goal)
    draw.text(((width - text_width) // 2, (height - text_height) // 2), goal, font=font, fill='red')
    return img

# Updated main function
def main():
    parser = argparse.ArgumentParser(description='Generate a labyrinth')
    parser.add_argument('width', type=int, help='Width of the labyrinth')
    parser.add_argument('height', type=int, help='Height of the labyrinth')
    args = parser.parse_args()
    width = args.width
    height = args.height
    wall_thickness = 20
    labyrinth = generate_iterative_random_maze(width, height, wall_thickness)
    img = draw_updated_labyrinth(labyrinth, wall_thickness)
    img.save("labyrinth.png")
    print("Labyrinth saved to labyrinth.png")

if __name__ == '__main__':
    main()

