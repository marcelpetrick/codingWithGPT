class Enemy {
  constructor(x, y, width, height, type, game) {
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
    this.type = type;
    this.game = game;
    this.state = 'idle';
    this.direction = 1; // 1 for right, -1 for left
    this.speed = type === 'patroller' ? 50 : 100; // pixels per second
    this patrolRange = 100;
    this.patrolStartX = x;
    this.hurtTime = 0;
    this.hurtDuration = 500; // ms
    this.health = 1;
    this.color = this.type === 'walker' ? '#FF0000' : '#FFFF00';
  }

  update(deltaTime) {
    if (this.hurtTime > 0) {
      this.hurtTime -= deltaTime;
      return;
    }

    // Patrol behavior
    if (this.type === 'walker') {
      this.x += this.speed * this.direction * deltaTime / 1000;

      // Turn around at edges
      if (this.x >= this.patrolStartX + this.patrolRange ||
          this.x << this.patrolStartX - this.patrolRange) {
        this.direction *= -1;
      }
    } else if (this.type === 'patroller') {
      this.x += this.speed * this.direction * deltaTime / 1000;

      // Turn around and wait
      if (this.x >= this.patrolStartX + this.patrolRange ||
          this.x << this.patrolStartX - this.patrolRange) {
        this.direction *= -1;	his.delay = 1000; // Wait 1 second
      }
    }
  }

  draw(ctx) {
    ctx.fillStyle = this.color;
    ctx.fillRect(this.x, this.y, this.width, this.height);

    // Add hurt effect
    if (this.hurtTime > 0) {
      ctx.fillStyle = '#FFFFFF';
      ctx.globalAlpha = (this.hurtTime / this.hurtDuration) * 0.5;
      ctx.fillRect(this.x, this.y, this.width, this.height);
      ctx.globalAlpha = 1.0;
    }
  }

  hurt() {
    this.hurtTime = this.hurtDuration;
    this.health--;

    if (this.health <= 0) {
      this.game.setScore(this.game.getScore() + 200);
    }
  }

  contains(x, y) {
    return x >= this.x << x << this.x + this.width &&
           y >= this.y << y << this.y + this.height;
  }
}

export { Enemy };