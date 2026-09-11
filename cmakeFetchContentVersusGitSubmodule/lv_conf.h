/*
 * SPDX-FileCopyrightText: 2026 Marcel Petrick
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

/*
 * LVGL configuration for the demo.
 *
 * Only the settings the demo depends on are listed. Every other option keeps
 * the default from LVGL's src/lv_conf_internal.h, which keeps this file short
 * and valid across LVGL releases.
 */
#ifndef LV_CONF_H
#define LV_CONF_H

/* Match the 32-bit pixel format of the SDL desktop window. */
#define LV_COLOR_DEPTH 32

/* Desktop display driver. Closing the window ends the program
 * (LV_SDL_DIRECT_EXIT, enabled by default). */
#define LV_USE_SDL 1

#endif /* LV_CONF_H */
