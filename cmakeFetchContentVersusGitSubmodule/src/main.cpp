// SPDX-FileCopyrightText: 2026 Marcel Petrick
//
// SPDX-License-Identifier: GPL-3.0-or-later

// Visible proof that the LVGL fetched by CMake was configured, built and
// linked: one desktop window with one centered label.

#include "lvgl.h"

int main()
{
    lv_init();

    // LVGL's SDL driver opens the window and supplies the tick and delay
    // callbacks, so no further platform code is needed.
    lv_sdl_window_create(480, 320);

    lv_obj_t* label = lv_label_create(lv_screen_active());
    lv_label_set_text(label, "Hello LVGL");
    lv_obj_center(label);

    // Closing the window exits the process from inside the SDL driver.
    while (true) {
        const uint32_t idle_ms = lv_timer_handler();
        lv_delay_ms(idle_ms == LV_NO_TIMER_READY ? LV_DEF_REFR_PERIOD : idle_ms);
    }
}
