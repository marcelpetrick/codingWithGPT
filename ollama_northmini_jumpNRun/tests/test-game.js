// Basic game functionality tests
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Game from '../src/game/Game.js';
import InputManager from '../src/input/InputManager.js';
import Player from '../src/entities/Player.js';

describe('Game Core Functionality', () => {
  let game;
  let inputManager;

  beforeEach(() => {
    // Create mock canvas
    const mockCanvas = {
      width: 800,
      height: 400,
      getContext: () => ({
        fillStyle: '',
        fillRect: () => {},
        drawImage: () => {},
        fillText: () => {},
        save: () => {},
        restore: () => {},
        translate: () => {},
        rotate: () => {},
        scale: () => {},
        beginPath: () => {},
        moveTo: () => {},
        lineTo: () => {},
        stroke: () => {},
      }),
    };

    game = new Game(mockCanvas);
    inputManager = new InputManager();
  });

  afterEach(() => {
    if (game) {
      game.destroy();
    }
  });

  it('should initialize game with correct properties', () => {
    expect(game.isRunning).toBe(false);
    expect(game.isPaused).toBe(false);
    expect(game.getScore()).toBe(0);
    expect(game.getLives()).toBe(3);
    expect(game.currentLevel).toBe(1);
  });

  it('should start and stop game loop', () => {
    game.start();
    expect(game.isRunning).toBe(true);

    game.pause();
    expect(game.isPaused).toBe(true);
  });

  it('should handle input manager updates', () => {
    inputManager.update(16.67);
    expect(inputManager.isKeyPressed('ArrowRight')).toBe(false);

    // Simulate key press
    inputManager.keys['ArrowRight'] = true;
    expect(inputManager.isKeyPressed('ArrowRight')).toBe(true);
  });

  it('should create player with correct initial state', () => {
    const player = new Player(game);
    expect(player.x).toBe(100);
    expect(player.y).toBe(200);
    expect(player.width).toBe(32);
    expect(player.height).toBe(48);
    expect(player.state).toBe('idle');
    expect(player.facing).toBe('right');
  });
});

describe('Physics Engine Tests', () => {
  import PhysicsEngine from '../src/physics/PhysicsEngine.js';

  it('should update physics with gravity', () => {
    const physics = new PhysicsEngine();

    // Create a dynamic object
    const obj = {
      x: 100,
      y: 100,
      width: 32,
      height: 32,
      body: {
        type: 'dynamic',
        velocity: { x: 0, y: 0 },
        enabled: true,
      },
    };

    physics.addObject(obj);
    physics.update(1000); // 1 second

    // Object should have gained downward velocity from gravity
    expect(obj.body.velocity.y).toBeGreaterThan(0);
  });

  it('should detect collisions between objects', () => {
    const physics = new PhysicsEngine();

    const objA = {
      x: 100,
      y: 100,
      width: 32,
      height: 32,
      body: { type: 'dynamic', enabled: true, velocity: { x: 0, y: 0 } },
    };

    const objB = {
      x: 150, // Overlapping with objA
      y: 100,
      width: 32,
      height: 32,
      body: { type: 'dynamic', enabled: true, velocity: { x: 0, y: 0 } },
    };

    physics.addObject(objA);
    physics.addObject(objB);

    physics.update(16.67);

    // Objects should be colliding
    expect(physics.checkCollision(objA, objB)).toBe(true);
  });
});

describe('Level Manager Tests', () => {
  import LevelManager from '../src/levels/LevelManager.js';

  it('should load first level with correct objects', () => {
    const game = {
      setLevel: (name) => {},
      player: { x: 100, y: 200, width: 32, height: 48, velocity: { x: 0, y: 0 } },
      setScore: (score) => {},
      getScore: () => 0,
      setLives: (lives) => {},
      getLives: () => 3,
    };

    const levelManager = new LevelManager(game);
    levelManager.loadLevel(0);

    expect(levelManager.currentLevel).toBeDefined();
    expect(levelManager.platforms).toBeDefined();
    expect(levelManager.coins).toBeDefined();
    expect(levelManager.enemies).toBeDefined();
  });
});

describe('UI System Tests', () => {
  import UIManager from '../src/ui/UIManager.js';

  it('should initialize UI manager', () => {
    const ui = new UIManager();
    expect(ui.showPause).toBe(false);
    expect(ui.showGameOver).toBe(false);
    expect(ui.showStart).toBe(false);
    expect(ui.getScore()).toBe(0);
    expect(ui.getLives()).toBe(3);
  });

  it('should update score and lives', () => {
    const ui = new UIManager();
    ui.updateScore(500);
    ui.updateLives(1);

    expect(ui.getScore()).toBe(500);
    expect(ui.getLives()).toBe(1);
  });
});