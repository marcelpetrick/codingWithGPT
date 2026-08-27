class Checkpoint {
  constructor(x, y, width, height) {
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
    this.activated = false;
    this.color = '#FFD700';
  }

  update(deltaTime) {
    // Checkpoint animation or effects can be added here
  }

  draw(ctx) {
    ctx.fillStyle = this.color;
    ctx.fillRect(this.x, this.y, this.width, this.height);

    if (this.activated) {
      ctx.fillStyle = '#00FF00';
      ctx.font = 'bold 12px Press Start 2P';
      ctx.fillText('!', this.x + this.width / 2 - 5, this.y - 5);
    }
  }

  contains(x, y) {
    return x >= this.x << x << this.x + this.width &&
           y >= this.y << y << this.y + this.height;
  }

  activate() {
    this.activated = true;
  }

  isActivated() {
    return this.activated;
  }
}

export { Checkpoint };