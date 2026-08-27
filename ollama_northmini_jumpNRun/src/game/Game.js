import InputManager from '../input/InputManager.js';
import PhysicsEngine from '../physics/PhysicsEngine.js';
import Renderer from '../renderer/Renderer.js';
import LevelManager from '../levels/LevelManager.js';
import UIManager from '../ui/UIManager.js';

class Game {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');

    // Game state
    this.isRunning = false;
    this.isPaused = false;
    this.score = 0;
    this.lives = 3;
    this.currentLevel = 1;

    // Game systems
    this.inputManager = new InputManager();
    this.physicsEngine = new PhysicsEngine();
    this.renderer = new Renderer(this.canvas.width, this.canvas.height);
    this.levelManager = new LevelManager(this);
    this.uiManager = new UIManager(this);

    // Game loop timing
    this.lastTime = 0;
    this.accumulatedTime = 0;
    this.fixedTimeStep = 1000 / 60; // 60 FPS target
    this.maxFrameTime = 250; // Cap frame time to prevent spiral of death

    // Bind methods
    this.gameLoop = this.gameLoop.bind(this);
    this.handleResize = this.handleResize.bind(this);

    // Setup event listeners
    window.addEventListener('resize', this.handleResize);
    document.addEventListener('keydown', this.handleKeyDown.bind(this));
    document.addEventListener('keyup', this.handleKeyUp.bind(this));
  }

  start() {
    if (this.isRunning) return;

    this.isRunning = true;
    this.lastTime = performance.now();

    // Start game loop
    requestAnimationFrame(this.gameLoop);
  }

  gameLoop(currentTime) {
    if (!this.isRunning) return;

    // Calculate delta time
    let deltaTime = currentTime - this.lastTime;

    // Cap delta time to prevent spiral of death
    if (deltaTime > this.maxFrameTime) {
      deltaTime = this.maxFrameTime;
    }

    this.lastTime = currentTime;
    this.accumulatedTime += deltaTime;

    // Fixed timestep game loop
    while (this.accumulatedTime >= this.fixedTimeStep) {
      this.update(this.fixedTimeStep);
      this.accumulatedTime -= this.fixedTimeStep;
    }

    // Render the current frame
    this.render();

    // Schedule next frame
    if (!this.isPaused) {
      requestAnimationFrame(this.gameLoop);
    }
  }

  update(deltaTime) {
    if (this.isPaused) return;

    // Update game systems
    this.inputManager.update(deltaTime);
    this.physicsEngine.update(deltaTime);
    this.levelManager.update(deltaTime);

    // Check win/lose conditions
    this.checkGameConditions();
  }

  render() {
    // Clear canvas
    this.ctx.fillStyle = '#000000';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Render game world
    this.renderer.render();

    // Render UI
    this.uiManager.render();
  }

  handleKeyDown(event) {
    this.inputManager.handleKeyDown(event);
  }

  handleKeyUp(event) {
    this.inputManager.handleKeyUp(event);
  }

  handleResize() {
    this.canvas.width = 800;
    this.canvas.height = 400;
    this.renderer.resize(this.canvas.width, this.canvas.height);
  }

  checkGameConditions() {
    // Check if player has died
    if (this.lives <= 0) {
      this.gameOver();
    }

    // Check level completion
    if (this.levelManager.isLevelComplete()) {
      this.nextLevel();
    }
  }

  gameOver() {
    this.isRunning = false;
    this.uiManager.showGameOver(this.score);
  }

  nextLevel() {
    this.currentLevel++;
    this.levelManager.loadLevel(this.currentLevel);
  }

  pause() {
    this.isPaused = true;
    this.uiManager.showPauseScreen();
  }

  resume() {
    this.isPaused = false;
    this.uiManager.hidePauseScreen();
    if (this.isRunning) {
      this.start();
    }
  }

  getScore() {
    return this.score;
  }

  setScore(score) {
    this.score = score;
    this.uiManager.updateScore(score);
  }

  getLives() {
    return this.lives;
  }

  setLives(lives) {
    this.lives = lives;
    this.uiManager.updateLives(lives);
  }

  destroy() {
    // Cleanup
    window.removeEventListener('resize', this.handleResize);
    document.removeEventListener('keydown', this.handleKeyDown);
    document.removeEventListener('keyup', this.handleKeyUp);
    this.isRunning = false;
  }
}

export default Game;