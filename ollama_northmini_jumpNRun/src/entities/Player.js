import { Body } from '../physics/Body.js';

class Player {
  constructor(game) {
    this.game = game;
    this.x = 100;
    this.y = 200;
    this.width = 32;
    this.height = 48;

    // Movement properties
    this.velocity = { x: 0, y: 0 };
    this.acceleration = { x: 500, y: 0 }; // pixels per second squared
    this.maxSpeed = { x: 200, y: 400 }; // pixels per second

    // State
    this.state = 'idle'; // idle, walking, jumping, falling, hitting
    this.facing = 'right';
    this.jumpCount = 0;
    this.doubleJumpAvailable = false;

    // Animation
    this.frameCount = 0;
    this.frameTime = 0;
    this.currentFrame = 0;
    this.animationSpeed = 0.15; // seconds per frame

    // Physics body
    this.body = new Body({
      type: 'dynamic',
      x: this.x,
      y: this.y,
      width: this.width,
      height: this.height,
      mass: 1,
      friction: 0.8,
      restitution: 0.2
    });

    // Input state
    this.isMovingLeft = false;
    this.isMovingRight = false;
    this.isJumping = false;
    this.isDoubleJumping = false;
  }

  update(deltaTime, input) {
    // Update physics body position
    this.body.x = this.x;
    this.body.y = this.y;

    // Handle input-based movement
    this.handleInput(deltaTime, input);

    // Update physics simulation
    this.updatePhysics(deltaTime);

    // Update state and animations
    this.updateState();
    this.updateAnimation(deltaTime);

    // Sync position from physics
    this.x = this.body.x;
    this.y = this.body.y;
  }

  handleInput(deltaTime, input) {
    const moveSpeed = this.acceleration.x * deltaTime / 1000;

    // Horizontal movement with acceleration/deceleration
    if (input.isKeyPressed('ArrowLeft') || input.isKeyPressed('KeyA')) {
      this.isMovingLeft = true;
      this.isMovingRight = false;
      this.facing = 'left';

      this.velocity.x = Math.max(this.velocity.x - moveSpeed, -this.maxSpeed.x);
    } else if (input.isKeyPressed('ArrowRight') || input.isKeyPressed('KeyD')) {
      this.isMovingLeft = false;
      this.isMovingRight = true;
      this.facing = 'right';

      this.velocity.x = Math.min(this.velocity.x + moveSpeed, this.maxSpeed.x);
    } else {
      // Deceleration
      const deceleration = this.acceleration.x * deltaTime / 1000;
      if (this.velocity.x > 0) {
        this.velocity.x = Math.max(0, this.velocity.x - deceleration);
      } else if (this.velocity.x < 0) {
        this.velocity.x = Math.min(0, this.velocity.x + deceleration);
      }

      this.isMovingLeft = false;
      this.isMovingRight = false;
    }

    // Jumping with coyote time and jump buffering
    if ((input.isKeyPressed('Space') || input.isKeyPressed('ArrowUp') || input.isKeyPressed('KeyZ') || input.isMousePressed()) &&
        (this.jumpCount < 2 || this.doubleJumpAvailable)) {

      if (this.jumpCount === 0) {
        // First jump
        this.velocity.y = -350;
        this.jumpCount = 1;
        this.state = 'jumping';
      } else if (this.jumpCount === 1 && this.doubleJumpAvailable) {
        // Double jump
        this.velocity.y = -300;
        this.jumpCount = 2;
        this.isDoubleJumping = true;
        this.state = 'jumping';
      }
    }

    // Ground check for coyote time
    if (this.isGrounded()) {
      this.jumpCount = 0;
      this.doubleJumpAvailable = true;
      this.isDoubleJumping = false;
    }
  }

  updatePhysics(deltaTime) {
    // Apply physics to body
    this.body.velocity.x = this.velocity.x;
    this.body.velocity.y = this.velocity.y;

    // Update body position using physics engine
    this.body.x += this.body.velocity.x * deltaTime / 1000;
    this.body.y += this.body.velocity.y * deltaTime / 1000;

    // Update our coordinates
    this.x = this.body.x;
    this.y = this.body.y;
  }

  updateState() {
    if (!this.isGrounded()) {
      if (this.velocity.y < 0) {
        this.state = 'jumping';
      } else {
        this.state = 'falling';
      }
    } else {
      if (this.isMovingLeft || this.isMovingRight) {
        this.state = 'walking';
      } else {
        this.state = 'idle';
      }
    }

    if (this.state === 'hitting') {
      this.frameCount = 0;
    }
  }

  updateAnimation(deltaTime) {
    this.frameTime += deltaTime;
    if (this.frameTime >= this.animationSpeed * 1000) {
      this.frameCount++;
      this.currentFrame = (this.frameCount % 4) + 1;
      this.frameTime = 0;
    }
  }

  isGrounded() {
    // Check if player is touching a platform
    // This would be implemented with collision detection
    return this.y + this.height >= 350 && this.velocity.y >= 0;
  }

  takeDamage() {
    // This would be called when player is hit by enemy
    this.game.setLives(this.game.getLives() - 1);
    this.state = 'hitting';
    this.x = 100;
    this.y = 200;
    this.velocity.x = 0;
    this.velocity.y = 0;
  }

  collectCollectible() {
    this.game.setScore(this.game.getScore() + 100);
  }

  die() {
    // Game over sequence
    this.game.gameOver();
  }

  getCurrentAnimationFrame() {
    return {
      x: this.x,
      y: this.y,
      width: this.width,
      height: this.height,
      state: this.state,
      facing: this.facing,
      frame: this.currentFrame
    };
  }
}

export default Player;