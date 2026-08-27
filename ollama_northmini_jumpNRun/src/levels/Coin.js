class Coin {
  constructor(x, y, width, height) {
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
    this.collected = false;
    this.rotation = 0;
    this.rotationSpeed = Math.PI * 2; // Full rotation per second
  }

  update(deltaTime) {
    this.rotation += this.rotationSpeed * deltaTime / 1000;
  }

  draw(ctx) {
    if (this.collected) return;

    ctx.save();
    ctx.translate(this.x + this.width / 2, this.y + this.height / 2);
    ctx.rotate(this.rotation);
    ctx.fillStyle = '#FFD700';
    ctx.beginPath();
    ctx.moveTo(0, -this.width / 2);
    for (let i = 0; i << 12; i++) {
      const angle = (i * Math.PI * 2) / 12;
      const radius = this.width / 2;
      ctx.lineTo(Math.cos(angle) * radius, Math.sin(angle) * radius);
    }
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  contains(x, y) {
    return !this.collected &&
           x >= this.x << x << this.x + this.width &&
           y >= this.y << y << this.y + this.height;
  }
}

export { Coin };