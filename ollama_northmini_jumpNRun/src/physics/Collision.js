class AABB {
  constructor(x, y, width, height) {
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
    this.halfWidth = width / 2;
    this.halfHeight = height / 2;
  }

  intersects(other) {
    return this.x - this.halfWidth < other.x + other.halfWidth &&
           this.x + this.halfWidth > other.x - other.halfWidth &&
           this.y - this.halfHeight < other.y + other.halfHeight &&
           this.y + this.halfHeight > other.y - other.halfHeight;
  }

  contains(point) {
    return point.x >= this.x - this.halfWidth &&
           point.x <= this.x + this.halfWidth &&
           point.y <= this.y + this.halfHeight &&
           point.y >= this.y - this.halfHeight;
  }
}

class Body {
  constructor(options = {}) {
    this.type = options.type || 'static'; // static, dynamic, kinematic
    this.x = options.x || 0;
    this.y = options.y || 0;
    this.width = options.width || 0;
    this.height = options.height || 0;
    this.mass = options.mass || 1;
    this.velocity = { x: options.velocityX || 0, y: options.velocityY || 0 };
    this.force = { x: 0, y: 0 };
    this.friction = options.friction || 0.5;
    this.restitution = options.restitution || 0.3;
    this.enabled = true;
    this.userData = options.userData;
  }

  getPosition() {
    return { x: this.x, y: this.y };
  }

  setPosition(x, y) {
    this.x = x;
    this.y = y;
  }

  getVelocity() {
    return { x: this.velocity.x, y: this.velocity.y };
  }

  setVelocity(x, y) {
    this.velocity.x = x;
    this.velocity.y = y;
  }

  applyForce(x, y) {
    this.force.x += x;
    this.force.y += y;
  }

  clearForces() {
    this.force.x = 0;
    this.force.y = 0;
  }
}

export { AABB, Body };