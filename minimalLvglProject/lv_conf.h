#ifndef LV_CONF_H
#define LV_CONF_H

/* Color depth: 8, 16, 24, or 32 */
#define LV_COLOR_DEPTH 32

/* OS abstraction — none for a plain desktop loop */
#define LV_USE_OS LV_OS_NONE

/* Heap: use LVGL's built-in allocator, 8 MB */
#define LV_USE_STDLIB_MALLOC  LV_STDLIB_BUILTIN
#define LV_USE_STDLIB_STRING  LV_STDLIB_BUILTIN
#define LV_USE_STDLIB_SPRINTF LV_STDLIB_BUILTIN
#define LV_MEM_SIZE (8 * 1024 * 1024U)

/* SDL2 display + input backend */
#define LV_USE_SDL           1
#define LV_SDL_INCLUDE_PATH  <SDL2/SDL.h>
#define LV_SDL_FULLSCREEN    0
#define LV_SDL_ZOOM          1
#define LV_SDL_DIRECT_EXIT   1   /* close window → exit() */

/* Logging */
#define LV_USE_LOG     1
#define LV_LOG_LEVEL   LV_LOG_LEVEL_WARN
#define LV_LOG_PRINTF  1

/* Fonts — enable Montserrat at multiple sizes */
#define LV_FONT_MONTSERRAT_14 1
#define LV_FONT_MONTSERRAT_16 1
#define LV_FONT_MONTSERRAT_20 1
#define LV_FONT_DEFAULT &lv_font_montserrat_14

/* Widgets used in the demo */
#define LV_USE_LABEL  1
#define LV_USE_BUTTON 1
#define LV_USE_SLIDER 1
#define LV_USE_BAR    1

/* Layout engines */
#define LV_USE_FLEX 1
#define LV_USE_GRID 1

#endif /* LV_CONF_H */
