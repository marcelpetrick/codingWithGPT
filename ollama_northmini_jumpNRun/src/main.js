// Main game entry point
import CoreGame from './game/CoreGame.js';

// Wait for DOM to be fully loaded before initializing the game
window.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('gameCanvas');
  if (!canvas) {
    console.error('Canvas element not found');
    return;
  }

  // Initialize the core game
  const game = new CoreGame(canvas);

  // Start the game with start screen
  game.startGame();
});

// Error handling for the game
window.addEventListener('error', (event) => {
  console.error('Game error:', event.error);
  // Optionally display error message to user
});

// Handle game visibility changes (browser tab switching)
window.addEventListener('visibilitychange', (event) => {
  if (document.hidden) {
    // Game is paused when tab is hidden
    if (game && game.getGameState() === 'playing') {
      game.pauseGame();
    }
  } else {
    // Resume game when tab is visible
    if (game && game.getGameState() === 'paused') {
      game.resumeGame();
    }
  }
});

export { CoreGame };