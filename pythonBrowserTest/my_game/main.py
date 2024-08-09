import pygame
import sys
import random

# Constants for screen dimensions and colors
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
BACKGROUND_COLOR = (34, 139, 34)  # Green background
SNAKE_COLOR = (0, 255, 0)  # Green snake
FRUIT_COLOR = (255, 0, 0)  # Red fruit
FONT_COLOR = (255, 255, 255)  # White text
SNAKE_SIZE = 10
FPS = 15


class Game:
    """Main game class that handles game phases, event handling, and rendering."""

    def __init__(self):
        """Initialize the game, set up the screen, clock, font, and initial game state."""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Snake Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.phase = "WELCOME"  # Initial phase is the welcome screen
        self.snake = Snake()
        self.fruit = Fruit()
        self.score = 0

    def run(self):
        """Main loop to run the game, handling events, updating game state, and rendering."""
        while True:
            self.handle_events()
            self.update()
            self.render()
            pygame.display.flip()
            self.clock.tick(FPS)

    def handle_events(self):
        """Handle user input and game events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif self.phase == "WELCOME" and event.type == pygame.MOUSEBUTTONDOWN:
                self.phase = "PLAYING"  # Start the game when the user clicks on the welcome screen

    def update(self):
        """Update the game state based on the current phase."""
        if self.phase == "PLAYING":
            self.snake.update()
            if self.snake.check_collision(self.fruit.position):
                self.score += 1
                self.snake.grow()
                self.fruit.reposition(self.snake)
                if self.score >= 3:
                    self.phase = "GAME_OVER"  # End the game after eating 3 fruits

    def render(self):
        """Render the current state of the game to the screen."""
        self.screen.fill(BACKGROUND_COLOR)
        if self.phase == "WELCOME":
            self.render_welcome_screen()
        elif self.phase == "PLAYING":
            self.snake.draw(self.screen)
            self.fruit.draw(self.screen)
            self.render_score()
        elif self.phase == "GAME_OVER":
            self.render_game_over_screen()

    def render_welcome_screen(self):
        """Render the welcome screen."""
        welcome_text = self.font.render("Welcome to the Snake Game!", True, FONT_COLOR)
        instruction_text = self.font.render("Click to Start", True, FONT_COLOR)
        self.screen.blit(welcome_text, ((SCREEN_WIDTH - welcome_text.get_width()) // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(instruction_text,
                         ((SCREEN_WIDTH - instruction_text.get_width()) // 2, SCREEN_HEIGHT // 2 + 10))

    def render_score(self):
        """Render the current score on the screen."""
        score_text = self.font.render(f"Score: {self.score}", True, FONT_COLOR)
        self.screen.blit(score_text, (SCREEN_WIDTH - score_text.get_width() - 10, 10))

    def render_game_over_screen(self):
        """Render the game over screen."""
        game_over_text = self.font.render("Game Over", True, FONT_COLOR)
        final_score_text = self.font.render(f"Final Score: {self.score}", True, FONT_COLOR)
        self.screen.blit(game_over_text, ((SCREEN_WIDTH - game_over_text.get_width()) // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(final_score_text,
                         ((SCREEN_WIDTH - final_score_text.get_width()) // 2, SCREEN_HEIGHT // 2 + 10))


class Snake:
    """Class representing the snake in the game."""

    def __init__(self):
        """Initialize the snake with a starting position."""
        self.body = [(100, 100)]  # Starting position
        self.direction = (0, 0)  # Initial direction (not used since snake follows mouse)

    def update(self):
        """Update the snake's position to follow the mouse."""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        new_head = (mouse_x // SNAKE_SIZE * SNAKE_SIZE, mouse_y // SNAKE_SIZE * SNAKE_SIZE)
        if new_head != self.body[0]:
            self.body.insert(0, new_head)
            self.body.pop()  # Remove the last segment unless the snake has eaten a fruit

    def grow(self):
        """Grow the snake by adding a new segment."""
        self.body.append(self.body[-1])  # Append a segment at the snake's tail

    def draw(self, screen):
        """Draw the snake on the screen."""
        for segment in self.body:
            pygame.draw.rect(screen, SNAKE_COLOR, (*segment, SNAKE_SIZE, SNAKE_SIZE))

    def check_collision(self, position):
        """Check if the snake's head has collided with a given position (e.g., the fruit)."""
        return self.body[0] == position


class Fruit:
    """Class representing the fruit in the game."""

    def __init__(self):
        """Initialize the fruit at a random position."""
        self.position = self.random_position()

    def random_position(self):
        """Generate a random position for the fruit on the grid."""
        return (random.randint(0, (SCREEN_WIDTH - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE,
                random.randint(0, (SCREEN_HEIGHT - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE)

    def reposition(self, snake):
        """Reposition the fruit, ensuring it doesn't appear on the snake's body."""
        while True:
            self.position = self.random_position()
            if self.position not in snake.body:
                break  # Ensure fruit does not spawn on the snake

    def draw(self, screen):
        """Draw the fruit on the screen."""
        font = pygame.font.Font(None, 36)
        screen.blit(font.render("@", True, FRUIT_COLOR), self.position)


if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        pygame.quit()
        sys.exit()
