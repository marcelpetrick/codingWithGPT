from PIL import Image, ImageOps, ImageDraw
import numpy as np
from mazelib import Maze
from mazelib.generate.Prims import Prims
from mazelib.solve.BacktrackingDFS import BacktrackingDFS


def image_to_grid(img_path):
    """Convert a maze image to a 2D grid."""
    img = ImageOps.grayscale(Image.open(img_path))
    width, height = img.size
    grid = [[0 if img.getpixel((x, y)) == 255 else 1 for y in range(height)] for x in range(width)]
    return grid


def solve_with_mazelib(grid):
    """Solve the maze using mazelib."""
    m = Maze()
    m.grid = np.array(grid)
    m.start = (1, 0)
    m.end = (len(grid) // 2, len(grid[0]) // 2)
    m.solver = BacktrackingDFS()
    return m.solve()


def draw_solution_on_image(img_path, solution):
    """Draw the solution path on the maze image."""
    img = Image.open(img_path)
    draw = ImageDraw.Draw(img)
    if solution:
        draw.line(solution, fill="blue", width=2)
    img.save("labyrinth_solved_with_mazelib.png")
    img.show()


def main():
    # Convert the maze image to a 2D grid
    grid = image_to_grid("labyrinth.png")

    # Solve the maze using mazelib
    solution = solve_with_mazelib(grid)

    # Draw the solution on the image
    draw_solution_on_image("labyrinth.png", solution)


if __name__ == '__main__':
    main()
