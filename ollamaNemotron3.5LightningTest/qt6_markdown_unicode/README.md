# Markdown → Unicode Converter

A small Qt6 Widgets application that converts common markdown formatting to unicode characters for visual enhancement.

## Overview

This tool takes markdown text as input and applies a series of transformations to replace markdown syntax with unicode characters that provide visual emphasis while remaining readable. It's useful for quickly seeing how markdown might look when rendered with decorative unicode characters, or for generating visually-enhanced text for posts, documents, or presentations.

## Features

- **Input pane** (left): Enter or paste markdown text
- **Output pane** (right): Displays the converted unicode-enhanced text
- **Log panel** (bottom): Shows conversion status, errors, and processing information
- **640x480** default window size
- Handles common markdown elements:
  - Headings (`#` through `######`)
  - Bold (`**text**` or `__text__`)
  - Italic (`*text*` or `_text_`)
  - Unordered list items (`* item` or `- item`)
  - Blockquotes (`> text`)
  - Horizontal rules (`---` or `***`)
  - Inline code (`\`code\``)

## Building and Running

### Prerequisites

- Qt6 development libraries (version 6.0 or later)
- CMake (version 3.16 or later)
- A C++17 compatible compiler

### Build Instructions

```bash
# 1. Clone or navigate to the project directory
cd /path/to/qt6_markdown_unicode

# 2. Create a build directory and enter it
mkdir -p build && cd build

# 3. Run CMake to configure the project
cmake ..

# 4. Build the application
make

# 5. Run the executable
./markdown_unicode
```

### Alternative: Single-configuration build

```bash
cd /path/to/qt6_markdown_unicode
mkdir -p build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make
./markdown_unicode
```

### Running from source

If you have Qt6 qmake/moc setup, you can also run directly:
```bash
qmake
make
./markdown_unicode
```

## Usage

1. Launch the application — a window will appear at **640x480 pixels**
2. The **left pane** accepts markdown input with placeholder text showing supported syntax
3. As you type or edit the markdown, the **right pane** updates in real-time with unicode-enhanced output
4. The **bottom log panel** shows:
   - Conversion status messages
   - Character count before and after conversion
   - Error notifications if conversion fails
   - Timestamped logs of processing activity

### Example Input/Output

**Input:**
```
# Hello World

This is **bold** text and *italic* here.

- Item one
- Item two

> This is a blockquote

--- 

`inline code`
```

**Output:** (unicode-enhanced version with box-drawing characters, bullet points, bracketed emphasis, etc.)

## Design Notes

- The converter processes text **line by line**, applying transformations in a prioritized order
- Headings are converted first to avoid interference from other patterns
- Bold and italic conversions handle the most common markdown syntax
- List items get unicode bullet points (•)
- Horizontal rules become box-drawing lines (━━━━━━━━━━━━━━━━━━━━━━)
- The converter is best-effort — not all markdown elements are supported, and results may vary
- Edge cases and unsupported syntax pass through unchanged

## Customization

To modify the conversion behavior:

1. Edit `src/main.cpp` to adjust the `MarkdownToUnicodeConverter` class
2. The conversion functions are modular — you can enable/disable specific transformations
3. Unicode characters used can be changed by modifying the `QChar` constants in the converter methods

## License

This project is available under the MIT License. See the LICENSE file for details.

## Contact

For issues, feature requests, or contributions, please use the issue tracker on the repository.