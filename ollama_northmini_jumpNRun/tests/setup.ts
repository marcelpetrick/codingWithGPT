// Vitest setup file
import { vi } from 'vitest';

// Mock canvas for testing
const mockCanvas = {
  width: 800,
  height: 400,
  getContext: vi.fn(() => ({
    fillStyle: '',
    fillRect: vi.fn(),
    drawImage: vi.fn(),
    fillText: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    translate: vi.fn(),
    rotate: vi.fn(),
    scale: vi.fn(),
    font: '',
    textAlign: 'left',
    textBaseline: 'middle',
  })),
});

// Setup global mocks
Object.defineProperty(globalThis, 'canvas', {
  value: mockCanvas,
});

// Mock Audio for sound tests
Object.defineProperty(globalThis, 'Audio', {
  value: vi.fn(() => ({
    play: vi.fn(),
    pause: vi.fn(),
    currentTime: 0,
    load: vi.fn(),
    oncanplaythrough: null,
    onerror: null,
  })),
});

// Image mock for assets
class MockImage {
  constructor() {
    this.onload = null;
    this.onerror = null;
    this.src = '';
    this.width = 0;
    this.height = 0;
  }
}

Object.defineProperty(globalThis, 'Image', {
  value: MockImage,
});

// Mock requestAnimationFrame for game loop testing
let animationFrameCallbacks = [];

Object.defineProperty(globalThis, 'requestAnimationFrame', {
  value: (callback) => {
    const id = setTimeout(() =u003e {
      const now = performance.now();
      callback(now);
    }, 16);
    animationFrameCallbacks.push(id);
    return id;
  },
});

Object.defineProperty(globalThis, 'cancelAnimationFrame', {
  value: (id) => {
    clearTimeout(id);
    const index = animationFrameCallbacks.indexOf(id);
    if (index > -1) {
      animationFrameCallbacks.splice(index, 1);
    }
  },
});

// Clean up animation frames after each test
afterEach(() =u003e {
  animationFrameCallbacks.forEach(id =u003e clearTimeout(id));
  animationFrameCallbacks = [];
});

// Mock performance.now for timing
const originalPerformance = performance;
Object.defineProperty(performance, 'now', {
  value: vi.fn(() =u003e Date.now()),
});

// Restore performance after tests
afterAll(() =u003e {
  Object.defineProperty(performance, 'now', {
    value: originalPerformance.now,
  });
});

// Setup test environment
export { mockCanvas };