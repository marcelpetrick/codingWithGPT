# Ollama Northmini Jump n Run

A 2D side-scrolling platformer browser game inspired by classic platformers like Super Mario Land.

## Game Overview

Navigate through challenging levels as you collect coins, avoid enemies, and reach the end of each stage. The game features smooth movement, precise platforming, and engaging gameplay mechanics.

## Key Features

- **Precise Platformer Mechanics**: Jump buffering, coyote time, acceleration-based movement
- **Multiple Game Modes**: Single-player campaign with 3 challenging levels
- **Collectibles & Scoring**: Collect coins for points, defeat enemies for bonus rewards
- **Visual Polish**: Pixel-art aesthetics with smooth animations and effects
- **Responsive Controls**: Keyboard-first controls with Firefox optimization
- **Progress Tracking**: Lives system, checkpoints, and level completion tracking

## Technical Specifications

- **Target Platform**: Web browser (optimized for Firefox desktop)
- **Rendering**: Canvas-based 2D graphics with pixel-perfect rendering
- **Physics**: Custom physics engine with fixed timestep for consistent gameplay
- **Dependencies**: Minimal stack for maximum performance

## Development Setup

### Prerequisites

- Node.js 18 or higher
- Modern web browser (Firefox recommended)

### Installation

```bash
# Clone the repository
cgit clone <repository-url>
cd ollama-northmini-jumpnrun

# Install dependencies
npm install
```

### Running the Game

```bash
# Start development server
npm run dev

# Open browser and visit http://localhost:3000
```

### Building for Production

```bash
# Build for production
npm run build

# Serve the built files
npm run serve
```\n
### Testing

```bash
# Run unit tests
npm run test

# Run browser tests (including Firefox)
npm run test:firefox

# Lint and type checking
npm run lint
npm run type-check
```

## Game Controls

- **Arrow Keys or A/D**: Move left and right
- **Space or Up Arrow**: Jump (with coyote time and jump buffering)
- **Z Key**: Secondary jump for double-jump
- **Escape**: Pause the game
- **R Key**: Restart level after game over

## Game Levels

1. **Forest Path**: Introduction to platforming with walking enemies
2. **Mountain Passage**: Challenging terrain with patroller enemies
3. **Castle Keep**: Final castle level with multiple boss-type enemies

## Game Mechanics

### Movement

- **Acceleration**: Smooth acceleration and deceleration when moving
- **Max Speed**: Cap on maximum movement speed for predictable gameplay
- **Coyote Time**: Brief period after leaving ground where you can still jump
- **Jump Buffering**: Allow jumping slightly before pressing jump button

### Combat

- **Ground Pound**: Jump on enemies on the ground to defeat them
- **Enemy Patterns**: Walking enemies patrol paths, patroller enemies move back and forth
- **Collision Detection**: Precise collision detection for platforming challenges

### Collectibles

- **Coins**: Collect coins for 100 points each
- **Checkpoints**: Checkpoint saves progress, returns to last checkpoint on death
- **Bonus Points**: Defeat enemies for additional points

## Architecture

The game is built with a modular architecture:

- **Game Core**: Main game loop and state management
- **Input System**: Keyboard and mouse input handling
- **Physics Engine**: Custom physics simulation with collision detection
- **Renderer**: Canvas-based rendering with pixel-perfect graphics
- **Level Manager**: Manages game levels, platforms, enemies, and collectibles
- **UI System**: HUD, pause screens, and game over screens

## Performance

The game is optimized for performance:

- **Fixed Timestep**: Consistent physics regardless of frame rate
- **Canvas Rendering**: Efficient 2D graphics rendering
- **Memory Management**: Minimal memory allocation during gameplay
- **Asset Management**: Pre-loaded game assets for smooth gameplay

## Browser Compatibility

The game is primarily developed for Firefox desktop with consideration for:

- Chrome and Edge
- Safari (desktop only)
- Mobile browsers (limited functionality)

For the best experience, use Firefox desktop.

## Known Issues

- Some advanced browser features may not be fully supported in all browsers
- Mobile performance may be limited by device capabilities
- Sound effects are limited due to browser autoplay restrictions

## Future Enhancements

Potential future features:

- Additional levels and game modes
- Power-ups and abilities
- Sound effects and background music
- High score tracking and leaderboards
- Settings menu and graphics options
- Mobile support with touch controls

## License

This project is part of the Coding with GPT initiative, focusing on autonomous game development.

## Credits

This project is based on the vision documented in `vision.md` and follows the autonomous development guidelines.