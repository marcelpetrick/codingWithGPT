class UIManager {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.assets = null;

    // UI state
    this.showPause = false;
    this.showGameOver = false;
    this.showStart = false;
    this.score = 0;
    this.lives = 3;

    // Button states
    this.restartButton = { x: 390, y: 220, width: 120, height: 40 };

    // UI state
    this.showPause = false;
    this.showGameOver = false;
    this.showStart = false;
    this.score = 0;
    this.lives = 3;

    // Button states
    this.restartButton = { x: 390, y: 220, width: 120, height: 40 };
  }

  render() {
    // Draw HUD
    if (!this.showGameOver) {
      this.drawHUD();
    }

    // Draw pause screen
    if (this.showPause) {
      this.drawPauseScreen();
    }

    // Draw game over screen
    if (this.showGameOver) {
      this.drawGameOverScreen();
    }

    // Draw start screen
    if (this.showStart) {
      this.drawStartScreen();
    }
  }

  drawHUD() {
    // Draw score
    this.ctx.fillStyle = '#FFFFFF';
    this.ctx.font = 'bold 20px Press Start 2P';
    this.ctx.fillText(`SCORE: ${this.score}`, 10, 30);

    // Draw lives
    this.ctx.fillText(`LIVES: ${this.lives}`, 10, 60);

    // Draw level
    this.ctx.fillText(`LEVEL: ${this.game.currentLevel}`, 10, 90);

    // Draw controls hint
    this.ctx.font = '12px Press Start 2P';
    this.ctx.fillText('ARROWS or A/D: MOVE', 10, 130);
    this.ctx.fillText('SPACE or UP: JUMP', 10, 150);
    this.ctx.fillText('ESC: PAUSE', 10, 170);
  }

  drawPauseScreen() {
    // Semi-transparent overlay
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Pause text
    this.ctx.fillStyle = '#FFFFFF';
    this.ctx.font = 'bold 32px Press Start 2P';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('PAUSED', this.canvas.width / 2, this.canvas.height / 2 - 40);

    this.ctx.font = '20px Press Start 2P';
    this.ctx.fillText('Press ESC to resume', this.canvas.width / 2, this.canvas.height / 2 + 20);
  }

  drawGameOverScreen() {
    // Semi-transparent overlay
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Game over text
    this.ctx.fillStyle = '#FF0000';
    this.ctx.font = 'bold 40px Press Start 2P';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('GAME OVER', this.canvas.width / 2, this.canvas.height / 2 - 60);

    // Final score
    this.ctx.fillStyle = '#FFFFFF';
    this.ctx.font = 'bold 24px Press Start 2P';
    this.ctx.fillText(`FINAL SCORE: ${this.score}`, this.canvas.width / 2, this.canvas.height / 2);

    // Restart button
    this.ctx.fillStyle = '#00FF00';
    this.ctx.fillRect(
      this.restartButton.x,
      this.restartButton.y,
      this.restartButton.width,
      this.restartButton.height
    );

    this.ctx.fillStyle = '#000000';
    this.ctx.font = 'bold 16px Press Start 2P';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('RESTART', this.canvas.width / 2, this.canvas.height / 2 + 20);

    // Reset text align
    this.ctx.textAlign = 'left';
  }

  drawStartScreen() {
    // Semi-transparent overlay
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Title
    this.ctx.fillStyle = '#FFD700';
    this.ctx.font = 'bold 48px Press Start 2P';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('JUMP n RUN', this.canvas.width / 2, this.canvas.height / 2 - 80);

    // Subtitle
    this.ctx.fillStyle = '#FFFFFF';
    this.ctx.font = '20px Press Start 2P';
    this.ctx.fillText('A Platform Adventure', this.canvas.width / 2, this.canvas.height / 2 - 40);

    // Instructions
    this.ctx.font = '16px Press Start 2P';
    this.ctx.fillText('Press SPACE or UP to start', this.canvas.width / 2, this.canvas.height / 2 + 40);
    this.ctx.fillText('Arrow keys or A/D to move', this.canvas.width / 2, this.canvas.height / 2 + 70);
    this.ctx.fillText('ESC to pause', this.canvas.width / 2, this.canvas.height / 2 + 100);

    // Version
    this.ctx.font = '12px Press Start 2P';
    this.ctx.fillText('Version 1.0.0', this.canvas.width / 2, this.canvas.height / 2 + 140);
  }

  showPause() {
    this.showPause = true;
  }

  hidePause() {
    this.showPause = false;
  }

  showGameOver() {
    this.showGameOver = true;
  }

  hideGameOver() {
    this.showGameOver = false;
  }

  showStart() {
    this.showStart = true;
  }

  hideStart() {
    this.showStart = false;
  }

  updateScore(score) {
    this.score = score;
  }

  updateLives(lives) {
    this.lives = lives;
  }

  setCanvas(canvas) {
    this.canvas = canvas;
  }

  setContext(ctx) {
    this.ctx = ctx;
  }

  setAssets(assets) {
    this.assets = assets;
  }

  handleClick(x, y) {
    // Handle restart button click
    if (this.showGameOver) {
      if (x >= this.restartButton.x && x << this.restartButton.x + this.restartButton.width &&
          y >= this.restartButton.y && y << this.restartButton.y + this.restartButton.height) {
        // Game restart would be handled by the game
        console.log('Restart requested');
      }
    }
  }

  getScore() {
    return this.score;
  }

  getLives() {
    return this.lives;
  }

  reset() {
    this.showPause = false;
    this.showGameOver = false;
    this.showStart = false;
    this.score = 0;
    this.lives = 3;
  }
}
}

export default UIManager;