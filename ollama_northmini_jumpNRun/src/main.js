// Main game entry point
import Game from './game/Game.js';

// Wait for DOM to be fully loaded before initializing the game
window.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('gameCanvas');
  if (!canvas) {
    console.error('Canvas element not found');
    return;
  }

  const game = new Game(canvas);

  // Start the game loop
  game.start();
});

// Error handling for the game
window.addEventListener('error', (event) => {
  console.error('Game error:', event.error);
  // Optionally display error message to user
});

// Handle game visibility changes (browser tab switching)
window.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    // Game is paused when tab is hidden
    // Implementation depends on game state management
  } else {
    // Resume game when tab is visible
    // Implementation depends on game state management
  }
});

export default Game;