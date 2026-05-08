#define SDL_MAIN_HANDLED
#include "lvgl/lvgl.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define WIN_W 800
#define WIN_H 480

static int          g_clicks = 0;
static lv_obj_t   * g_status;

static void on_button_click(lv_event_t * e)
{
    const char * name = lv_event_get_user_data(e);
    g_clicks++;
    char buf[80];
    snprintf(buf, sizeof(buf), "%s  |  total clicks: %d", name, g_clicks);
    lv_label_set_text(g_status, buf);
}

static void on_slider_change(lv_event_t * e)
{
    lv_obj_t * s = lv_event_get_target(e);
    char buf[32];
    snprintf(buf, sizeof(buf), "Slider value: %d%%", (int)lv_slider_get_value(s));
    lv_label_set_text(g_status, buf);
}

static void make_button(lv_obj_t * parent, const char * label_text, const char * id)
{
    lv_obj_t * btn = lv_button_create(parent);
    lv_obj_set_size(btn, 160, 50);
    lv_obj_add_event_cb(btn, on_button_click, LV_EVENT_CLICKED, (void *)id);

    lv_obj_t * lbl = lv_label_create(btn);
    lv_label_set_text(lbl, label_text);
    lv_obj_center(lbl);
}

int main(void)
{
    setenv("DBUS_FATAL_WARNINGS", "0", 1);

    lv_init();

    lv_display_t * disp = lv_sdl_window_create(WIN_W, WIN_H);
    lv_sdl_mouse_create();
    lv_sdl_mousewheel_create();
    lv_sdl_keyboard_create();
    (void)disp;

    /* Dark background on the active screen */
    lv_obj_t * scr = lv_screen_active();
    lv_obj_set_style_bg_color(scr, lv_color_hex(0x1a1d27), 0);
    lv_obj_remove_flag(scr, LV_OBJ_FLAG_SCROLLABLE);

    /* Flex-column layout on the screen itself */
    lv_obj_set_flex_flow(scr, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_flex_align(scr,
        LV_FLEX_ALIGN_CENTER,   /* main axis: vertical centering */
        LV_FLEX_ALIGN_CENTER,   /* cross axis: horizontal centering */
        LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_row(scr, 28, 0);

    /* ── Title ── */
    lv_obj_t * title = lv_label_create(scr);
    lv_label_set_text(title, "LVGL Demo  –  Manjaro Linux");
    lv_obj_set_style_text_font(title, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(title, lv_color_hex(0xdde3f8), 0);

    /* ── Button row (transparent container, flex-row) ── */
    lv_obj_t * row = lv_obj_create(scr);
    lv_obj_set_size(row, LV_SIZE_CONTENT, LV_SIZE_CONTENT);
    lv_obj_set_style_bg_opa(row, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(row, 0, 0);
    lv_obj_set_style_pad_all(row, 0, 0);
    lv_obj_set_flex_flow(row, LV_FLEX_FLOW_ROW);
    lv_obj_set_style_pad_column(row, 16, 0);

    make_button(row, LV_SYMBOL_OK  " Accept",   "Accept");
    make_button(row, LV_SYMBOL_CLOSE " Cancel", "Cancel");
    make_button(row, LV_SYMBOL_SETTINGS " Config", "Config");

    /* ── Status line ── */
    g_status = lv_label_create(scr);
    lv_label_set_text(g_status, "Click a button or drag the slider");
    lv_obj_set_style_text_color(g_status, lv_color_hex(0x7882a0), 0);
    lv_obj_set_style_text_font(g_status, &lv_font_montserrat_14, 0);

    /* ── Slider ── */
    lv_obj_t * slider = lv_slider_create(scr);
    lv_obj_set_width(slider, 380);
    lv_slider_set_value(slider, 50, LV_ANIM_OFF);
    lv_obj_add_event_cb(slider, on_slider_change, LV_EVENT_VALUE_CHANGED, NULL);

    /* Main loop */
    while (1) {
        lv_timer_handler();
        lv_tick_inc(5);
        usleep(5000);   /* 5 ms → ~200 Hz refresh budget */
    }

    return 0;
}
