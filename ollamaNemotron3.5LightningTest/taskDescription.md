# Task: Markdown → Unicode Converter

## Overview

Build a small desktop application that converts markdown text into a visually enhanced unicode representation. The applicant is free to design the solution — the goal is to see how they approach a concrete problem, not to match a reference implementation.

## Requirements

### Must Have

- **Qt6** with **CMake** as the build system
- A GUI window with:
  - An input area where the user can type or paste markdown
  - A live-rendered output area showing the unicode-converted result
  - A log/status panel showing conversion feedback (success, errors, character counts)
- Support for common markdown elements:
  - Headings (`#` through `######`)
  - Bold (`**text**` or `__text__`)
  - Italic (`*text*` or `_text_`)
  - Strikethrough (`~~text~~`)
  - Unordered lists (`- item` or `* item`)
  - Numbered lists (`1. item`)
  - Blockquotes (`> text`)
  - Inline code (`` `code` ``)
  - Horizontal rules (`---`)
  - Code fences (`` ``` ``)
- Real-time conversion as the user types
- Clean, readable UI — no overlapping widgets, proper layout management
- A `README.md` explaining how to build and run the application

### Should Have

- Clear, well-structured code with meaningful comments
- Consistent coding style (linting where applicable)
- Proper error handling — no crashes on invalid input
- The unicode characters should actually render correctly in common fonts

### Nice to Have

- Keyboard shortcuts
- File open/save
- Theme switching (light/dark)
- Export functionality
- Customizable unicode mappings
- Tests

## Evaluation Criteria

- **Software craftsmanship**: code structure, naming, comments, consistency
- **Problem solving**: how they handle edge cases and ambiguous input
- **UI quality**: layout, spacing, visual hierarchy, usability
- **Qt/CMake proficiency**: correct use of the framework and build system
- **Documentation**: clarity of the README, code comments
- **Design decisions**: the choices they make and how well they justify them

## What We're Looking For

This is not a test of memorized API knowledge. We want to see:

- How they structure a project from scratch
- How they handle incremental refinement
- How they think about user experience
- How they write and organize code
- What questions they ask when requirements are ambiguous

Feel free to make assumptions and document them. The best submissions will show thoughtful design decisions, not just a working program.

## Deliverables

1. Source code in a git repository
2. `README.md` with build and run instructions
3. A brief design note explaining key decisions and trade-offs
