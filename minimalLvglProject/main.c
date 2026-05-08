#define SDL_MAIN_HANDLED
#include "lvgl.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define WIN_W 800
#define WIN_H 480

static int g_clicks = 0;
static lv_obj_t* g_status;

static void on_button_click(lv_event_t* e)
{
    const char* name = lv_event_get_user_data(e);
    g_clicks++;
    char buf[80];
    snprintf(buf, sizeof(buf), "%s  ·  total clicks: %d", name, g_clicks);
    lv_label_set_text(g_status, buf);
}

static void on_slider_change(lv_event_t* e)
{
    lv_obj_t* s = lv_event_get_target(e);
    char buf[32];
    snprintf(buf, sizeof(buf), "Power: %d%%", (int)lv_slider_get_value(s));
    lv_label_set_text(g_status, buf);
}

/* Semi-transparent glow blob — deliberately positioned to bleed off screen edges */
static void make_glow(lv_obj_t* parent, int w, int h, uint32_t color, lv_opa_t opa, int x, int y)
{
    lv_obj_t* o = lv_obj_create(parent);
    lv_obj_set_size(o, w, h);
    lv_obj_set_style_radius(o, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(o, lv_color_hex(color), 0);
    lv_obj_set_style_bg_opa(o, opa, 0);
    lv_obj_set_style_border_width(o, 0, 0);
    lv_obj_set_style_shadow_width(o, 0, 0);
    lv_obj_set_pos(o, x, y);
}

static void make_accent_button(lv_obj_t* parent, const char* text, const char* id, uint32_t color)
{
    lv_obj_t* btn = lv_button_create(parent);
    lv_obj_set_size(btn, 155, 46);
    lv_obj_set_style_bg_color(btn, lv_color_hex(color), LV_STATE_DEFAULT);
    lv_obj_set_style_radius(btn, 12, 0);
    /* Colored drop-shadow gives buttons a "glowing" feel */
    lv_obj_set_style_shadow_color(btn, lv_color_hex(color), 0);
    lv_obj_set_style_shadow_width(btn, 20, 0);
    lv_obj_set_style_shadow_opa(btn, LV_OPA_40, 0);
    lv_obj_add_event_cb(btn, on_button_click, LV_EVENT_CLICKED, (void*)id);

    lv_obj_t* lbl = lv_label_create(btn);
    lv_label_set_text(lbl, text);
    lv_obj_center(lbl);
}

int main(void)
{
    setenv("DBUS_FATAL_WARNINGS", "0", 1);

    lv_init();
    lv_display_t* disp = lv_sdl_window_create(WIN_W, WIN_H);
    lv_sdl_mouse_create();
    lv_sdl_mousewheel_create();
    lv_sdl_keyboard_create();
    (void)disp;

    /* ── Screen: deep-space vertical gradient ──────────────────────────── */
    lv_obj_t* scr = lv_screen_active();
    lv_obj_remove_flag(scr, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_bg_color(scr, lv_color_hex(0x0d0221), 0);
    lv_obj_set_style_bg_grad_color(scr, lv_color_hex(0x1c0a3a), 0);
    lv_obj_set_style_bg_grad_dir(scr, LV_GRAD_DIR_VER, 0);

    /* ── Glow blobs — drawn first so they sit behind the card ──────────── */
    /* violet, top-right corner */
    make_glow(scr, 440, 440, 0x7c3aed, 38, WIN_W - 240, -170);
    /* cyan, bottom-left corner */
    make_glow(scr, 380, 380, 0x06b6d4, 31, -150, WIN_H - 220);
    /* amber accent, bottom-center */
    make_glow(scr, 210, 210, 0xf59e0b, 20, WIN_W / 2 - 105, WIN_H - 95);

    /* ── Glassmorphism card ─────────────────────────────────────────────── */
    lv_obj_t* card = lv_obj_create(scr);
    lv_obj_set_size(card, 620, 330);
    lv_obj_align(card, LV_ALIGN_CENTER, 0, 0);
    /* frosted-glass look: very transparent white fill + faint white border */
    lv_obj_set_style_bg_color(card, lv_color_white(), 0);
    lv_obj_set_style_bg_opa(card, LV_OPA_10, 0);
    lv_obj_set_style_border_color(card, lv_color_white(), 0);
    lv_obj_set_style_border_opa(card, LV_OPA_20, 0);
    lv_obj_set_style_border_width(card, 1, 0);
    lv_obj_set_style_radius(card, 24, 0);
    /* purple ambient shadow makes card float over the glows */
    lv_obj_set_style_shadow_width(card, 60, 0);
    lv_obj_set_style_shadow_color(card, lv_color_hex(0x7c3aed), 0);
    lv_obj_set_style_shadow_opa(card, LV_OPA_40, 0);
    lv_obj_set_style_pad_all(card, 28, 0);
    lv_obj_remove_flag(card, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_flex_flow(card, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_flex_align(card, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_row(card, 18, 0);

    /* Title */
    lv_obj_t* title = lv_label_create(card);
    lv_label_set_text(title, "LVGL - Embedded UI Demo");
    lv_obj_set_style_text_font(title, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(title, lv_color_hex(0xf1f5f9), 0);

    /* Thin separator */
    lv_obj_t* sep = lv_obj_create(card);
    lv_obj_set_size(sep, lv_pct(90), 2);
    lv_obj_set_style_bg_color(sep, lv_color_white(), 0);
    lv_obj_set_style_bg_opa(sep, LV_OPA_20, 0);
    lv_obj_set_style_border_width(sep, 0, 0);
    lv_obj_set_style_radius(sep, 0, 0);
    lv_obj_set_style_pad_all(sep, 0, 0);

    /* Button row */
    lv_obj_t* row = lv_obj_create(card);
    lv_obj_set_size(row, LV_SIZE_CONTENT, LV_SIZE_CONTENT);
    lv_obj_set_style_bg_opa(row, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(row, 0, 0);
    lv_obj_set_style_pad_all(row, 0, 0);
    lv_obj_set_flex_flow(row, LV_FLEX_FLOW_ROW);
    lv_obj_set_style_pad_column(row, 14, 0);

    make_accent_button(row, LV_SYMBOL_OK " Accept", "Accept", 0x10b981); /* emerald */
    make_accent_button(row, LV_SYMBOL_CLOSE " Cancel", "Cancel", 0xef4444); /* red     */
    make_accent_button(row, LV_SYMBOL_SETTINGS " Config", "Config", 0x6366f1); /* indigo  */

    /* Status label */
    g_status = lv_label_create(card);
    lv_label_set_text(g_status, "Click a button or drag the slider");
    lv_obj_set_style_text_color(g_status, lv_color_hex(0x94a3b8), 0);
    lv_obj_set_style_text_font(g_status, &lv_font_montserrat_14, 0);

    /* Slider — indicator tinted indigo, knob is near-white */
    lv_obj_t* slider = lv_slider_create(card);
    lv_obj_set_width(slider, 400);
    lv_slider_set_value(slider, 50, LV_ANIM_OFF);
    lv_obj_set_style_bg_color(slider, lv_color_hex(0x6366f1), LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(slider, lv_color_hex(0xf1f5f9), LV_PART_KNOB);
    lv_obj_add_event_cb(slider, on_slider_change, LV_EVENT_VALUE_CHANGED, NULL);

    while (1) {
        lv_timer_handler();
        lv_tick_inc(5);
        usleep(5000);
    }

    return 0;
}
