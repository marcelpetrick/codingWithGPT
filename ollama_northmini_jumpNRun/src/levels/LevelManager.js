import { Checkpoint } from './Checkpoint.js';
import { Coin } from './Coin.js';
import { Enemy } from './Enemy.js';
import { Platform } from './Platform.js';

class LevelManager {
  constructor(game) {
    this.game = game;
    this.levels = [
      {
        name: 'Forest Path',
        platforms: [[0, 350, 800, 50]],
        coins: [[240, 300, 20, 20]],
        enemies: [[520, 318, 32, 32, 'walker']],
        checkpoints: [[700, 300, 20, 50]],
      },
    ];
    this.currentLevel = null;
    this.platforms = [];
    this.coins = [];
    this.enemies = [];
    this.checkpoints = [];
    this.levelComplete = false;
  }

  loadLevel(index) {
    const level = this.levels[index];
    if (!level) {
      throw new RangeError(`Unknown level index: ${index}`);
    }

    this.currentLevel = level;
    this.platforms = level.platforms.map(args => new Platform(...args));
    this.coins = level.coins.map(args => new Coin(...args));
    this.enemies = level.enemies.map(args => new Enemy(...args, this.game));
    this.checkpoints = level.checkpoints.map(args => new Checkpoint(...args));
    this.levelComplete = false;
  }

  update(deltaTime) {
    for (const entity of [...this.platforms, ...this.coins, ...this.enemies, ...this.checkpoints]) {
      entity.update(deltaTime);
    }
  }

  isLevelComplete() {
    return this.levelComplete;
  }
}

export default LevelManager;
