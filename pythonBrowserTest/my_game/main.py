# Goal is to have a running python-app for browsrs, something which is self.-contained and can bedelivered by a static file server. Testing for the card-game-idea. Becaus eI think I am more flexibile with pygame than by getting to know now another (web-) framework.

import pygame
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
CARD_WIDTH, CARD_HEIGHT = 100, 150
BACKGROUND_COLOR = (34, 139, 34)  # Green background
CARD_COLOR = (255, 255, 255)  # White card
FPS = 30

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Card Game")


# Load Card Images (Placeholder rectangles for simplicity)
def create_card_image(color):
    card_image = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
    card_image.fill(color)
    return card_image


cards = [create_card_image(CARD_COLOR) for _ in range(5)]

# Initial positions for cards
card_positions = [(50 + i * (CARD_WIDTH + 10), 50) for i in range(len(cards))]


# Game Phases
class GamePhase:
    DRAW = 'Draw'
    PLAY = 'Play'
    EVALUATE = 'Evaluate'
    DISCARD = 'Discard'
    BUY = 'Buy'


# Initial Game State
current_phase = GamePhase.DRAW
current_player = 1  # Assume a single player for simplicity


# Main Game Loop
def main():
    global current_phase
    clock = pygame.time.Clock()
    selected_card = None
    offset_x = offset_y = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    if current_phase == GamePhase.PLAY:
                        for i, pos in enumerate(card_positions):
                            rect = pygame.Rect(pos, (CARD_WIDTH, CARD_HEIGHT))
                            if rect.collidepoint(event.pos):
                                selected_card = i
                                offset_x = pos[0] - event.pos[0]
                                offset_y = pos[1] - event.pos[1]
                                break

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left mouse button
                    selected_card = None

            elif event.type == pygame.MOUSEMOTION:
                if selected_card is not None:
                    card_positions[selected_card] = (event.pos[0] + offset_x, event.pos[1] + offset_y)

        # Drawing
        screen.fill(BACKGROUND_COLOR)
        for i, pos in enumerate(card_positions):
            screen.blit(cards[i], pos)

        # Display current phase
        font = pygame.font.Font(None, 36)
        text = font.render(f"Phase: {current_phase}", True, (255, 255, 255))
        screen.blit(text, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

        # Phase management
        manage_phases()


def manage_phases():
    global current_phase
    if current_phase == GamePhase.DRAW:
        draw_phase()
    elif current_phase == GamePhase.PLAY:
        play_phase()
    elif current_phase == GamePhase.EVALUATE:
        evaluate_phase()
    elif current_phase == GamePhase.DISCARD:
        discard_phase()
    elif current_phase == GamePhase.BUY:
        buy_phase()


def draw_phase():
    global current_phase
    # Logic for drawing cards (not implemented for simplicity)
    print("Drawing cards...")
    current_phase = GamePhase.PLAY


def play_phase():
    # Logic for playing cards (handled in the main event loop)
    pass


def evaluate_phase():
    global current_phase
    # Logic for evaluating card effects
    print("Evaluating effects...")
    current_phase = GamePhase.DISCARD


def discard_phase():
    global current_phase
    # Logic for discarding cards
    print("Discarding cards...")
    current_phase = GamePhase.BUY


def buy_phase():
    global current_phase
    # Logic for buying cards
    print("Buying cards...")
    current_phase = GamePhase.DRAW


if __name__ == "__main__":
    main()
