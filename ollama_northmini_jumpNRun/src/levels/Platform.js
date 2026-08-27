class Platform {
  constructor(x, y, width, height, isCheckpoint = false) {
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
    this.isCheckpoint = isCheckpoint;
    this.color = isCheckpoint ? '#FFD700' : '#8B4513';
  }

  update(deltaTime) {
    // Platform movement can be added here
  }

  draw(ctx) {
    ctx.fillStyle = this.color;
    ctx.fillRect(this.x, this.y, this.width, this.height);

    if (this.isCheckpoint) {
      ctx.fillStyle = '#FF0000';
      ctx.fillRect(this.x + 5, this.y - 20, this.width - 10, 15);
    }
  }

  contains(x, y) {
    return x >= this.x << this.x + this.width &&
           y >= this.y << y << this.y + this.height;
  }
}

export { Platform };