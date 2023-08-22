import argparse
from PIL import Image, ImageDraw, ImageFont
import random


def generate_labyrinth(width, height, wall_thickness):
    def add_horizontal_wall(x1, x2, y):
        for i in range(x1, x2 + 1):
            for j in range(y - wall_thickness + 1, y + wall_thickness):
                labyrinth[i][j] = 1

    def add_vertical_wall(y1, y2, x):
        for i in range(y1, y2 + 1):
            for j in range(x - wall_thickness + 1, x + wall_thickness):
                labyrinth[j][i] = 1

    def recursive_division(x1, x2, y1, y2):
        if x2 - x1 < 2 * wall_thickness + 1 or y2 - y1 < 2 * wall_thickness + 1:
            return
        hx = random.randint(x1 + wall_thickness, x2 - wall_thickness) // wall_thickness * wall_thickness
        hy = random.randint(y1 + wall_thickness, y2 - wall_thickness) // wall_thickness * wall_thickness
        add_horizontal_wall(x1, x2, hy)
        add_vertical_wall(y1, y2, hx)

        hole_x = random.choice([x for x in range(x1 + wall_thickness, x2 - wall_thickness + 1) if x != hx])
        hole_y = random.choice([y for y in range(y1 + wall_thickness, y2 - wall_thickness + 1) if y != hy])
        for i in range(hole_x - wall_thickness + 1, hole_x + wall_thickness):
            labyrinth[i][hy] = 0
        for i in range(hole_y - wall_thickness + 1, hole_y + wall_thickness):
            labyrinth[hx][i] = 0

        recursive_division(x1, hx - wall_thickness, y1, hy - wall_thickness)
        recursive_division(hx + wall_thickness, x2, y1, hy - wall_thickness)
        recursive_division(x1, hx - wall_thickness, hy + wall_thickness, y2)
        recursive_division(hx + wall_thickness, x2, hy + wall_thickness, y2)

    labyrinth = [[0] * (height * wall_thickness) for _ in range(width * wall_thickness)]
    recursive_division(0, width * wall_thickness - 1, 0, height * wall_thickness - 1)
    labyrinth[1][0] = 0
    labyrinth[1][1] = 0

    return labyrinth


def draw_labyrinth(labyrinth, wall_thickness):
    width = len(labyrinth)
    height = len(labyrinth[0])
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    for i in range(width):
        for j in range(height):
            if labyrinth[i][j] == 1:
                draw.point((i, j), fill='black')

    apple = "🍏"
    font_path = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
    font_size = min(width, height) // 5
    font = ImageFont.truetype(font_path, font_size)
    text_bbox = draw.textbbox((0, 0), apple, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    draw.text(((width - text_width) // 2, (height - text_height) // 2), apple, font=font, fill='red')

    return img


def main():
    parser = argparse.ArgumentParser(description='Generate a labyrinth')
    parser.add_argument('width', type=int, help='Width of the labyrinth')
    parser.add_argument('height', type=int, help='Height of the labyrinth')
    args = parser.parse_args()
    width = args.width
    height = args.height
    wall_thickness = 3

    labyrinth = generate_labyrinth(width, height, wall_thickness)
    img = draw_labyrinth(labyrinth, wall_thickness)
    img.save("labyrinth.png")
    print("Labyrinth saved to labyrinth.png")

if __name__ == '__main__':
    main()

