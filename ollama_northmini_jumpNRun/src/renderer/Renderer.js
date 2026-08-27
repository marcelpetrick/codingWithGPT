import { Assets } from '../core/Assets.js';

class Renderer {
  constructor(width, height) {
    this.width = width;
    this.height = height;
    this.canvas = null;
    this.ctx = null;
    this.debugMode = false;
  }

  resize(width, height) {
    this.width = width;
    this.height = height;
    if (this.canvas) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
  }

  render() {
    // This will be called by the game class
    // Components should register with the renderer
    // For now, this is a placeholder
  }

  clear() {
    if (this.ctx) {
      this.ctx.fillStyle = '#000000';
      this.ctx.fillRect(0, 0, this.width, this.height);
    }
  }

  drawImage(image, x, y, width, height, angle = 0) {
    if (!this.ctx || !image) return;

    this.ctx.save();
    this.ctx.translate(x + (width || image.width) / 2, y + (height || image.height) / 2);
    this.ctx.rotate(angle * Math.PI / 180);
    this.ctx.drawImage(image, -(width || image.width) / 2, -(height || image.height) / 2, width || image.width, height || image.height);
    this.ctx.restore();
  }

  drawRect(x, y, width, height, color, filled = true) {
    if (!this.ctx) return;

    this.ctx.save();
    this.ctx.fillStyle = color;
    this.ctx.strokeStyle = color;
    if (filled) {
      this.ctx.fillRect(x, y, width, height);
    } else {
      this.ctx.strokeRect(x, y, width, height);
    }
    this.ctx.restore();
  }

  drawText(text, x, y, color, fontSize, align = 'left') {
    if (!this.ctx) return;

    this.ctx.save();
    this.ctx.font = `bold ${fontSize}px Press Start 2P`;
    this.ctx.fillStyle = color;
    this.ctx.textAlign = align;
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText(text, x, y);
    this.ctx.restore();
  }

  drawLine(x1, y1, x2, y2, color, lineWidth = 1) {
    if (!this.ctx) return;

    this.ctx.save();
    this.ctx.strokeStyle = color;
    this.ctx.lineWidth = lineWidth;
    this.ctx.beginPath();
    this.ctx.moveTo(x1, y1);
    this.ctx.lineTo(x2, y2);
    this.ctx.stroke();
    this.ctx.restore();
  }

  setDebugMode(enabled) {
    this.debugMode = enabled;
  }

  drawDebugInfo(game) {
    if (!this.debugMode || !game) return;

    // Draw debug information
    this.drawText(`FPS: ${Math.round(game.fps)}`, 10, 20, '#00FF00', 12);
    this.drawText(`Delta: ${game.deltaTime.toFixed(2)}`, 10, 40, '#00FF00', 12);
    this.drawText(`Objects: ${game.physicsEngine ? game.physicsEngine.getObjectCount() : 0}`, 10, 60, '#00FF00', 12);
  }

  drawSprite(sprite, x, y, scale = 1, rotation = 0) {
    if (!this.ctx || !sprite) return;

    this.ctx.save();
    this.ctx.translate(x, y);
    this.ctx.scale(scale, scale);
    this.ctx.rotate(rotation);
    this.ctx.drawImage(sprite.image, -sprite.width / 2, -sprite.height / 2, sprite.width, sprite.height);
    this.ctx.restore();
  }
}

export default Renderer;