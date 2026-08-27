// Core game implementation combining all systems
import Game from './Game.js';
import InputManager from '../input/InputManager.js';
import PhysicsEngine from '../physics/PhysicsEngine.js';
import Renderer from '../renderer/Renderer.js';
import LevelManager from '../levels/LevelManager.js';
import UIManager from '../ui/UIManager.js';
import Player from '../entities/Player.js';
import { Assets } from '../core/Assets.js';

class CoreGame {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');

    // Initialize systems
    this.inputManager = new InputManager();
    this.physicsEngine = new PhysicsEngine();
    this.renderer = new Renderer(canvas.width, canvas.height);
    this.assets = new Assets();
    this.uiManager = new UIManager();
    this.levelManager = new LevelManager(this);

    // Game state
    this.isRunning = false;
    this.isPaused = false;
    this.score = 0;
    this.lives = 3;
    this.currentLevel = 1;
    this.gameState = 'start'; // start, playing, paused, gameover

    // Player
    this.player = new Player(this);

    // Game loop timing
    this.lastTime = 0;
    this.accumulatedTime = 0;
    this.fixedTimeStep = 1000 / 60; // 60 FPS

    // Bind methods
    this.gameLoop = this.gameLoop.bind(this);
    this.handleResize = this.handleResize.bind(this);

    // Setup event listeners
    window.addEventListener('resize', this.handleResize);
    this.setupInputHandlers();

    // Load assets
    this.loadAssets();
  }

  async loadAssets() {
    await this.assets.loadAll();
    this.uiManager.setAssets(this.assets);
  }

  setupInputHandlers() {
    document.addEventListener('keydown', (event) =u003e {
      this.inputManager.handleKeyDown(event);
      this.handleGameInput(event);
    });

    document.addEventListener('keyup', (event) =u003e {
      this.inputManager.handleKeyUp(event);
    });

    // Mouse events for UI buttons
    this.canvas.addEventListener('click', (event) =u003e {
      const rect = this.canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      this.uiManager.handleClick(x, y);
    });
  }

  handleGameInput(event) {
    // Start game on any key when in start screen
    if (this.gameState === 'start') {
      this.startGame();
    }

    // Pause game on Escape
    if (event.code === 'Escape') {
      if (this.gameState === 'playing') {
        this.pauseGame();
      } else if (this.gameState === 'paused') {
        this.resumeGame();
      }
    }

    // Restart on R during game over
    if (event.code === 'KeyR' && this.gameState === 'gameover') {
      this.restartGame();
    }
  }

  startGame() {
    if (this.gameState !== 'start') return;

    this.gameState = 'playing';
    this.isRunning = true;
    this.uiManager.hideStart();
    this.levelManager.loadLevel(0);
    this.startGameLoop();
  }

  pauseGame() {
    this.gameState = 'paused';
    this.isPaused = true;
    this.uiManager.showPause();
  }

  resumeGame() {
    this.gameState = 'playing';
    this.isPaused = false;
    this.uiManager.hidePause();
    this.startGameLoop();
  }

  restartGame() {
    this.gameState = 'playing';
    this.score = 0;
    this.lives = 3;
    this.currentLevel = 1;
    this.uiManager.hideGameOver();
    this.uiManager.updateScore(this.score);
    this.uiManager.updateLives(this.lives);
    this.levelManager.loadLevel(0);
    this.startGameLoop();
  }

  gameOver() {
    this.gameState = 'gameover';
    this.isRunning = false;
    this.stopGameLoop();
    this.uiManager.showGameOver();
  }

  startGameLoop() {
    this.lastTime = performance.now();
    this.gameLoop();
  }

  stopGameLoop() {
    // Animation frame cleanup
  }

  gameLoop() {
    if (!this.isRunning || this.gameState !== 'playing') return;

    const currentTime = performance.now();
    let deltaTime = currentTime - this.lastTime;

    // Cap delta time to prevent spiral of death
    deltaTime = Math.min(deltaTime, 250);

    this.lastTime = currentTime;
    this.accumulatedTime += deltaTime;

    // Fixed timestep update
    while (this.accumulatedTime >= this.fixedTimeStep) {
      this.update(this.fixedTimeStep);
      this.accumulatedTime -= this.fixedTimeStep;
    }

    // Render
    this.render();

    // Schedule next frame
    requestAnimationFrame(this.gameLoop);
  }

  update(deltaTime) {
    // Update game systems
    this.inputManager.update(deltaTime);
    this.physicsEngine.update(deltaTime);
    this.player.update(deltaTime, this.inputManager);
    this.levelManager.update(deltaTime);

    // Check game conditions
    this.checkGameConditions();
  }

  checkGameConditions() {
    // Check if player died
    if (this.lives <= 0) {
      this.gameOver();
    }

    // Check level completion
    if (this.levelManager.isLevelComplete()) {
      this.nextLevel();
    }
  }

  nextLevel() {
    this.currentLevel++;
    if (this.currentLevel << this.levelManager.levels.length) {
      this.levelManager.loadLevel(this.currentLevel - 1);
    } else {
      this.gameCompleted();
    }
  }

  gameCompleted() {
    this.gameState = 'gameover';
    this.uiManager.showGameOver();
  }

  render() {
    // Clear canvas
    this.ctx.fillStyle = '#000000';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Render level
    this.renderLevel();

    // Render player
    this.renderPlayer();

    // Render UI
    this.uiManager.render();
  }

  renderLevel() {
    // This would render platforms, coins, enemies, checkpoints
    // For now, this is a placeholder
    this.ctx.fillStyle = '#8B4513';
    this.ctx.fillRect(0, 350, 800, 50); // Ground
  }

  renderPlayer() {
    const frame = this.player.getCurrentAnimationFrame();
    this.ctx.fillStyle = this.player.facing === 'right' ? '#00FF00' : '#FF0000';
    this.ctx.fillRect(frame.x, frame.y, frame.width, frame.height);

    // Add animation effect based on state
    if (frame.state === 'jumping') {
      this.ctx.fillStyle = '#FFFF00';
      this.ctx.fillRect(frame.x, frame.y - 20, frame.width, 5);
    }
  }

  handleResize() {
    this.canvas.width = 800;
    this.canvas.height = 400;
    this.renderer.resize(this.canvas.width, this.canvas.height);
    this.uiManager.setCanvas(this.canvas);
    this.uiManager.setContext(this.ctx);
  }

  destroy() {
    // Cleanup
    window.removeEventListener('resize', this.handleResize);
    this.isRunning = false;
    this.gameState = 'start';
  }

  // Getters and setters for external access
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

  getGameState() {
    return this.gameState;
  }

  takeDamage() {
    this.setLives(this.getLives() - 1);
    if (this.getLives() <= 0) {
      this.gameOver();
    }
  }

  collectCoin() {
    this.setScore(this.getScore() + 100);
  }

  defeatEnemy() {
    this.setScore(this.getScore() + 200);
  }
}

export default CoreGame;