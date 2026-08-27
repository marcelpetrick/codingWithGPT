class CollisionSystem {
  constructor() {
    this.collisions = [];
  }

  update(objects) {
    this.collisions = [];

    for (let i = 0; i < objects.length; i++) {
      for (let j = i + 1; j < objects.length; j++) {
        const objA = objects[i];
        const objB = objects[j];

        if (this.checkCollision(objA, objB)) {
          this.collisions.push({ a: objA, b: objB });
          this.resolveCollision(objA, objB);
        }
      }
    }
  }

  checkCollision(objA, objB) {
    if (!objA || !objB) return false;

    // AABB collision check
    const aLeft = objA.x;
    const aRight = objA.x + objA.width;
    const aTop = objA.y;
    const aBottom = objA.y + objA.height;

    const bLeft = objB.x;
    const bRight = objB.x + objB.width;
    const bTop = objB.y;
    const bBottom = objB.y + objB.height;

    return aLeft < bRight &&
           aRight > bLeft &&
           aTop < bBottom &&
           aBottom > bTop;
  }

  resolveCollision(objA, objB) {
    const objADx = objB.x - objA.x + objB.width / 2 - objA.width / 2;
    const objADy = objB.y - objA.y + objB.height / 2 - objA.height / 2;

    const objBDx = -objADx;
    const objBDy = -objADy;

    if (objA.body && objB.body) {
      // Simple elastic collision
      const totalMass = objA.body.mass + objB.body.mass;

      // Update positions to resolve overlap
      const overlapX = (objA.width + objB.width) / 2 - Math.abs(objADx);
      const overlapY = (objA.height + objB.height) / 2 - Math.abs(objADy);

      if (Math.abs(objADx) > Math.abs(objADy)) {
        // Resolve horizontal collision
        const push = overlapX / 2;
        if (objADx < 0) {
          objA.x += push;
          objB.x -= push;
        } else {
          objA.x -= push;
          objB.x += push;
        }
      } else {
        // Resolve vertical collision
        const push = overlapY / 2;
        if (objADy < 0) {
          objA.y += push;
          objB.y -= push;
        } else {
          objA.y -= push;
          objB.y += push;
        }
      }

      // Simple velocity exchange for demonstration
      const tempVx = objA.body.velocity.x;
      const tempVy = objA.body.velocity.y;
      objA.body.velocity.x = objB.body.velocity.x;
      objA.body.velocity.y = objB.body.velocity.y;
      objB.body.velocity.x = tempVx;
      objB.body.velocity.y = tempVy;
    }
  }

  getCollisions() {
    return this.collisions;
  }
}

export default CollisionSystem;