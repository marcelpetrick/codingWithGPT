class InputManager {
  constructor() {
    this.keys = {};
    this.mouse = { x: 0, y: 0, pressed: false };
    this.jumpBuffer = [];
    this.jumpBufferTime = 300; // ms
    this.jumpCooldown = 0;

    this.setupEventListeners();
  }

  setupEventListeners() {
    // Keyboard input
    document.addEventListener('keydown', (event) => {
      this.keys[event.code] = true;

      // Jump buffering
      if (event.code === 'Space' || event.code === 'ArrowUp' || event.code === 'KeyZ') {
        this.jumpBuffer.push(event.timeStamp);
      }
    });

    document.addEventListener('keyup', (event) => {
      this.keys[event.code] = false;
    });

    // Mouse input
    document.addEventListener('mousedown', (event) => {
      this.mouse.pressed = true;
    });

    document.addEventListener('mouseup', (event) => {
      this.mouse.pressed = false;
    });

    document.addEventListener('mousemove', (event) => {
      this.mouse.x = event.clientX;
      this.mouse.y = event.clientY;
    });
  }

  update(deltaTime) {
    this.jumpCooldown = Math.max(0, this.jumpCooldown - deltaTime);
  }

  isKeyPressed(key) {
    return this.keys[key] || false;
  }

  getJumpInput() {
    return this.jumpBuffer.length > 0;
  }

  consumeJumpInput() {
    this.jumpBuffer = [];
  }

  isMousePressed() {
    return this.mouse.pressed;
  }

  getMousePosition() {
    return { x: this.mouse.x, y: this.mouse.y };
  }
}

export default InputManager;