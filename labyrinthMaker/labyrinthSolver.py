from PIL import Image, ImageOps, ImageDraw
from queue import PriorityQueue

class MazeSolver:
    def __init__(self, image_path):
        self.image_path = image_path
        self.maze = self.load_maze()
        self.start = (1, 0)
        self.goal = (len(self.maze) // 2, len(self.maze[0]) // 2)
        self.solution = []

    def load_maze(self):
        img = ImageOps.grayscale(Image.open(self.image_path))
        return [[0 if img.getpixel((x, y)) == 255 else 1 for y in range(img.height)] for x in range(img.width)]

    @staticmethod
    def is_goal(node, goal):
        return node == goal

    @staticmethod
    def heuristic(node, goal):
        return abs(node[0] - goal[0]) + abs(node[1] - goal[1])

    def get_neighbors(self, node):
        neighbors = []
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        for dx, dy in directions:
            x, y = node[0] + dx, node[1] + dy
            if 0 <= x < len(self.maze) and 0 <= y < len(self.maze[0]) and self.maze[x][y] == 0:
                neighbors.append((x, y))
        return neighbors

    def solve(self):
        open_list = PriorityQueue()
        open_list.put((0, self.start))
        came_from = {}
        g_score = {(x, y): float('inf') for x in range(len(self.maze)) for y in range(len(self.maze[0]))}
        g_score[self.start] = 0
        f_score = {(x, y): float('inf') for x in range(len(self.maze)) for y in range(len(self.maze[0]))}
        f_score[self.start] = self.heuristic(self.start, self.goal)

        while not open_list.empty():
            _, current = open_list.get()
            if self.is_goal(current, self.goal):
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                self.solution = path[::-1]
                return self.solution
            for neighbor in self.get_neighbors(current):
                temp_g_score = g_score[current] + 1
                if temp_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = temp_g_score
                    f_score[neighbor] = temp_g_score + self.heuristic(neighbor, self.goal)
                    open_list.put((f_score[neighbor], neighbor))
        return []

    def draw_solution(self):
        img = Image.open(self.image_path)
        draw = ImageDraw.Draw(img)
        if self.solution:
            draw.line(self.solution, fill="blue", width=2)
        return img

def main():
    solver = MazeSolver("labyrinth.png")
    solver.solve()
    solved_img = solver.draw_solution()
    #solved_img.show()
    solved_img.save("labyrinth_solved.png")

if __name__ == '__main__':
    main()
