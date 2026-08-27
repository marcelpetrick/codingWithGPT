class Assets {
  constructor() {
    this.images = {};
    this.audio = {};
    this.sounds = {};
    this.loaded = false;
    this.loadingCount = 0;
    this.totalAssets = 0;
  }

  loadImage(key, src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () =u003e {
        this.images[key] = img;
        this.loadingCount++;
        resolve(img);
      };
      img.onerror = reject;
      img.src = src;
    });
  }

  loadSound(key, src) {
    return new Promise((resolve, reject) => {
      const audio = new Audio();
      audio.oncanplaythrough = () =u003e {
        this.sounds[key] = audio;
        this.loadingCount++;
        resolve(audio);
      };
      audio.onerror = reject;
      audio.src = src;
      audio.load();
    });
  }

  async loadAll() {
    // Load game assets
    await Promise.all([
      this.loadImage('player', '/assets/player.png'),
      this.loadImage('platform', '/assets/platform.png'),
      this.loadImage('coin', '/assets/coin.png'),
      this.loadImage('enemy', '/assets/enemy.png'),
      this.loadSound('jump', '/assets/sounds/jump.wav'),
      this.loadSound('coin', '/assets/sounds/coin.wav'),
      this.loadSound('hit', '/assets/sounds/hit.wav'),
      this.loadSound('gameOver', '/assets/sounds/gameover.wav'),
    ]);

    this.loaded = true;
  }

  isLoaded() {
    return this.loaded;
  }

  getImage(key) {
    return this.images[key];
  }

  getSound(key) {
    return this.sounds[key];
  }

  playSound(key) {
    if (this.sounds[key]) {
      this.sounds[key].currentTime = 0;
      this.sounds[key].play();
    }
  }

  stopAllSounds() {
    Object.values(this.sounds).forEach(sound => {
      sound.pause();
      sound.currentTime = 0;
    });
  }
}

export { Assets };