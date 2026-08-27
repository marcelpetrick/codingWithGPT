import { AABB, Body } from './Collision.js';

class PhysicsEngine {
  constructor() {
    this.objects = [];
    this.gravity = 2000; // pixels per second squared
    this.airResistance = 0.95;
    this.velocityIterations = 8;
    this.positionIterations = 8;
  }

  update(deltaTime) {
    const gravityAcceleration = (this.gravity * deltaTime) / 1000;

    // Update velocities with gravity
    for (let i = 0; i < this.velocityIterations; i++) {
      for (const obj of this.objects) {
        if (!obj.body || !obj.body.enabled) continue;

        // Apply gravity to dynamic objects
        if (obj.body.type === 'dynamic') {
          obj.body.velocity.y += gravityAcceleration;
        }

        // Apply air resistance
        if (obj.body.velocity.x !== 0) {
          obj.body.velocity.x *= this.airResistance;
        }
        if (obj.body.velocity.y !== 0) {
          obj.body.velocity.y *= this.airResistance;
        }
      }
    }

    // Update positions
    for (let i = 0; i < this.positionIterations; i++) {
      for (const obj of this.objects) {
        if (!obj.body || !obj.body.enabled) continue;

        const oldX = obj.x;
        const oldY = obj.y;

        obj.x += obj.body.velocity.x * deltaTime / 1000;
        obj.y += obj.body.velocity.y * deltaTime / 1000;

        // Handle screen wrapping if needed
        if (obj.x < -50) {
          obj.x = window.innerWidth;
        } else if (obj.x > window.innerWidth + 50) {
          obj.x = -50;
        }

        if (obj.y < -50) {
          obj.y = window.innerHeight;
        } else if (obj.y > window.innerHeight + 50) {
          obj.y = -50;
        }
      }
    }

    // Collision detection
    this.detectCollisions();
  }

  addObject(obj) {
    if (!this.objects.includes(obj)) {
      this.objects.push(obj);
    }
  }

  removeObject(obj) {
    const index = this.objects.indexOf(obj);
    if (index >= -1) {
      this.objects.splice(index, 1);
    }
  }

  detectCollisions() {
    for (let i = 0; i < this.objects.length; i++) {
      for (let j = i + 1; j < this.objects.length; j++) {
        const objA = this.objects[i];
        const objB = this.objects[j];

        if (this.checkCollision(objA, objB)) {
          this.resolveCollision(objA, objB);
        }
      }
    }
  }

  checkCollision(objA, objB) {
    if (!objA.body || !objB.body) return false;
    if (!objA.body.enabled || !objB.body.enabled) return false;

    // Simple AABB collision
    const aabbA = new AABB(objA.x, objA.y, objA.width, objA.height);
    const aabbB = new AABB(objB.x, objB.y, objB.width, objB.height);

    return aabbA.intersects(aabbB);
  }

  resolveCollision(objA, objB) {
    // Simple elastic collision response
    const objAX = objA.x + objA.width / 2;
    const objAY = objA.y + objA.height / 2;
    const objBX = objB.x + objB.width / 2;
    const objBY = objB.y + objB.height / 2;

    const objADx = objAX - objBX;
    const objADy = objAY - objBY;

    // Normalize collision direction
    const distance = Math.sqrt(objADx * objADx + objADy * objADy);
    if (distance === 0) return;

    const nx = objADx / distance;
    const ny = objADy / distance;

    // Push objects apart
    const objADepth = (objA.width + objB.width) / 2 - distance;
    const objBDepth = objADepth;

    if (objA.body && objB.body) {
      objA.x -= nx * objADepth * 0.5;
      objA.y -= ny * objADepth * 0.5;
      objB.x += nx * objBDepth * 0.5;
      objB.y += ny * objBDepth * 0.5;

      // Reflect velocities
      const relativeVelocityX = objB.body.velocity.x - objA.body.velocity.x;
      const relativeVelocityY = objB.body.velocity.y - objA.body.velocity.y;
      const velocityAlongNormal = relativeVelocityX * nx + relativeVelocityY * ny;

      if (velocityAlongNormal > 0) return;

      const impulse = -2 * velocityAlongNormal;
      objA.body.velocity.x += impulse * nx;
      objA.body.velocity.y += impulse * ny;
    }
  }

  getObjectCount() {
    return this.objects.length;
  }

  clear() {
    this.objects = [];
  }
}

export default PhysicsEngine;