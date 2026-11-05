#!/usr/bin/python3
"""
Vector Cairo and Pango renderer for the Water Plane notification banner.
Draws a vintage skywriter plane pulling an animated banner
with vector water droplets and sparkle particles.
Supports rock-solid, non-jiggling text with calm, smooth gliding physics.
"""

import math
import cairo
import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo


def draw_water_drop(cr, cx, cy, size=26):
    """Draw a glossy, shaded vector water droplet with specular reflections."""
    cr.save()
    cr.translate(cx, cy)
    s = size / 30.0
    cr.scale(s, s)

    # Teardrop contour
    cr.new_path()
    cr.move_to(0, -18)
    cr.curve_to(8, -8, 14, 2, 14, 9)
    cr.arc(0, 9, 14, 0, math.pi)
    cr.curve_to(-14, 2, -8, -8, 0, -18)
    cr.close_path()

    # Radial gradient body
    pat = cairo.RadialGradient(-3, 5, 2, 0, 9, 15)
    pat.add_color_stop_rgba(0.0, 0.45, 0.85, 1.0, 1.0)
    pat.add_color_stop_rgba(0.7, 0.15, 0.55, 0.95, 1.0)
    pat.add_color_stop_rgba(1.0, 0.05, 0.35, 0.8, 1.0)
    cr.set_source(pat)
    cr.fill_preserve()

    # Droplet outline
    cr.set_source_rgba(0.05, 0.3, 0.65, 0.95)
    cr.set_line_width(1.6 / s)
    cr.stroke()

    # Curved primary gloss highlight
    cr.new_path()
    cr.move_to(-4, -8)
    cr.curve_to(-8, -2, -10, 5, -8, 10)
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.85)
    cr.set_line_width(2.5 / s)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.stroke()

    # Small secondary specular glint
    cr.arc(5, 14, 1.8 / s, 0, 2 * math.pi)
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.7)
    cr.fill()

    cr.restore()


def draw_sparkle(cr, cx, cy, size=7, alpha=0.8):
    """Draw a 4-pointed diamond sparkle / water glint."""
    if alpha <= 0:
        return
    cr.save()
    cr.translate(cx, cy)
    cr.set_source_rgba(0.35, 0.78, 1.0, alpha)
    cr.new_path()
    cr.move_to(0, -size)
    cr.curve_to(0, -size * 0.2, -size * 0.2, 0, -size, 0)
    cr.curve_to(-size * 0.2, 0, 0, size * 0.2, 0, size)
    cr.curve_to(0, size * 0.2, size * 0.2, 0, size, 0)
    cr.curve_to(size * 0.2, 0, 0, -size * 0.2, 0, -size)
    cr.close_path()
    cr.fill()

    # Bright core
    cr.set_source_rgba(1.0, 1.0, 1.0, alpha)
    cr.arc(0, 0, size * 0.3, 0, 2 * math.pi)
    cr.fill()
    cr.restore()


class SceneRenderer:
    def __init__(self, message="TIME TO DRINK WATER! STAY HYDRATED", font_name="Sans Bold 16", direction="ltr"):
        self.message = message
        self.font_name = font_name
        self.direction = direction.lower()
        self.plane_length = 130
        self.plane_height = 42
        self.cable_length = 55
        self.banner_height = 56
        
        # Measure text using Pango once
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
        cr = cairo.Context(surface)
        pango_ctx = PangoCairo.create_context(cr)
        self.pango_layout = Pango.Layout(pango_ctx)
        font_desc = Pango.FontDescription(self.font_name)
        self.pango_layout.set_font_description(font_desc)
        self.pango_layout.set_text(self.message, -1)
        self.text_w, self.text_h = self.pango_layout.get_pixel_size()
        
        # Generous padding so text never crowds droplets
        self.banner_width = self.text_w + 140
        self.total_length = self.plane_length + self.cable_length + self.banner_width + 80

    def render(self, cr, plane_x, base_y, elapsed, bobbing=True):
        """
        Renders the complete flying plane, tow rope, banner, and particles.
        plane_x is the position of the nose of the plane.
        """
        if self.direction == "ltr":
            self._render_ltr(cr, plane_x, base_y, elapsed, bobbing)
        else:
            self._render_rtl(cr, plane_x, base_y, elapsed, bobbing)

    # -------------------------------------------------------------------------
    # LEFT TO RIGHT (LTR) RENDERING: Plane faces right, pulls banner behind on left
    # -------------------------------------------------------------------------
    def _render_ltr(self, cr, plane_x, base_y, elapsed, bobbing=True):
        # Very gentle, slow, serene cruising bobbing (5px amplitude, 1.2 frequency)
        bob = math.sin(elapsed * 1.2) * 5.0 if bobbing else 0.0
        pitch = math.cos(elapsed * 1.2) * 0.02 if bobbing else 0.0
        cur_plane_y = base_y + bob

        tail_x = plane_x - 122
        banner_front_x = tail_x - self.cable_length
        banner_back_x = banner_front_x - self.banner_width
        banner_y = base_y + (math.sin(elapsed * 1.2 - 0.4) * 5.0 if bobbing else 0.0)

        # 1. Exhaust smoke puffs trailing behind (to the left of plane tail)
        for i in range(6):
            puff_phase = elapsed * 3.0 + i * 0.85
            px = tail_x - 10 - i * 22 - math.sin(puff_phase) * 2
            py = cur_plane_y + 8 + math.sin(puff_phase * 0.6) * 3
            r = 7 + i * 3.2
            a = max(0.0, 0.48 - i * 0.075)
            if a > 0:
                pat = cairo.RadialGradient(px + r * 0.3, py - r * 0.3, 1, px, py, r)
                pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, a * 1.2)
                pat.add_color_stop_rgba(0.7, 0.9, 0.96, 1.0, a)
                pat.add_color_stop_rgba(1.0, 0.8, 0.92, 1.0, 0.0)
                cr.set_source(pat)
                cr.arc(px, py, r, 0, 2 * math.pi)
                cr.fill()

        # 2. Tow Cable: from tail to spreader bar at banner_front_x
        bridle_x = tail_x - 25
        cr.save()
        cr.set_source_rgba(0.2, 0.25, 0.3, 0.85)
        cr.set_line_width(1.8)
        cr.move_to(tail_x, cur_plane_y - 10)
        cr.line_to(bridle_x, cur_plane_y)
        cr.move_to(tail_x, cur_plane_y + 8)
        cr.line_to(bridle_x, cur_plane_y)
        cr.curve_to(bridle_x - 12, cur_plane_y + 4, banner_front_x + 12, banner_y + 2, banner_front_x, banner_y)
        cr.stroke()
        cr.restore()

        # 3. Banner
        self._render_banner_ltr(cr, banner_back_x, banner_front_x, banner_y, elapsed)

        # 4. Sparkles trailing behind banner (left of banner_back_x)
        sparkle_phase = elapsed * 3.5
        s1 = 0.5 + 0.5 * math.sin(sparkle_phase)
        s2 = 0.5 + 0.5 * math.sin(sparkle_phase + 2.0)
        s3 = 0.5 + 0.5 * math.sin(sparkle_phase + 4.0)
        draw_sparkle(cr, banner_back_x - 16, banner_y - 12, 7 + s1 * 2, 0.7 * s1 + 0.2)
        draw_sparkle(cr, banner_back_x - 36, banner_y + 15, 6 + s2 * 2, 0.7 * s2 + 0.2)
        draw_sparkle(cr, banner_back_x - 56, banner_y - 3, 8 + s3 * 2, 0.8 * s3 + 0.2)

        # 5. Airplane Facing Right
        cr.save()
        cr.translate(plane_x, cur_plane_y)
        cr.scale(-1, 1)        # Mirror horizontally so nose faces right
        cr.rotate(-pitch)
        self._render_plane_body(cr, elapsed)
        cr.restore()

    def _render_banner_ltr(self, cr, bx, banner_front_x, banner_y, elapsed):
        bw = self.banner_width
        bh = self.banner_height
        by = banner_y - bh / 2

        steps = 36
        wave_freq = 0.25
        wave_speed = 2.8   # Soft, slow undulating cloth wave (calm and smooth)
        wave_amp = 2.0     # Subtle 2px cloth wave at the edges

        top_pts = []
        bot_pts = []
        for i in range(steps + 1):
            cx = bx + (bw * i / steps)
            w = math.sin(elapsed * wave_speed + (steps - i) * wave_freq) * wave_amp
            top_pts.append((cx, by + w))
            bot_pts.append((cx, by + bh + w))

        cr.save()
        cr.new_path()
        # Swallowtail notch on LEFT edge (trailing)
        notch_x = bx + 24
        mid_y = (top_pts[0][1] + bot_pts[0][1]) / 2
        cr.move_to(notch_x, mid_y)
        cr.line_to(top_pts[0][0], top_pts[0][1])

        for pt in top_pts[1:]:
            cr.line_to(pt[0], pt[1])

        cr.line_to(bot_pts[-1][0], bot_pts[-1][1])

        for pt in reversed(bot_pts[:-1]):
            cr.line_to(pt[0], pt[1])

        cr.line_to(notch_x, mid_y)
        cr.close_path()

        # Banner cloth gradient
        b_pat = cairo.LinearGradient(bx, by, bx, by + bh)
        b_pat.add_color_stop_rgba(0.0, 0.98, 0.99, 1.0, 0.97)
        b_pat.add_color_stop_rgba(0.5, 0.94, 0.97, 1.0, 0.97)
        b_pat.add_color_stop_rgba(1.0, 0.88, 0.93, 0.98, 0.97)
        cr.set_source(b_pat)
        cr.fill_preserve()

        # Gentle cloth folds
        cr.save()
        cr.clip_preserve()
        for i in range(steps):
            x1 = top_pts[i][0]
            x2 = top_pts[i + 1][0]
            slope = math.cos(elapsed * wave_speed + (steps - i) * wave_freq)
            if slope > 0:
                cr.set_source_rgba(1.0, 1.0, 1.0, slope * 0.15)
            else:
                cr.set_source_rgba(0.0, 0.1, 0.3, -slope * 0.08)
            cr.rectangle(x1, by - 10, x2 - x1, bh + 20)
            cr.fill()
        cr.restore()

        # Banner crisp outline border
        cr.set_source_rgba(0.12, 0.45, 0.82, 0.95)
        cr.set_line_width(2.4)
        cr.stroke()

        # Wooden spreader bar at the front (right edge)
        cr.set_source_rgba(0.38, 0.24, 0.12, 1.0)
        cr.set_line_width(4.5)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(banner_front_x, top_pts[-1][1] - 2)
        cr.line_to(banner_front_x, bot_pts[-1][1] + 2)
        cr.stroke()

        for gy in [top_pts[-1][1] + 6, bot_pts[-1][1] - 6]:
            cr.arc(banner_front_x - 4, gy, 2.5, 0, 2 * math.pi)
            cr.set_source_rgba(0.85, 0.75, 0.2, 1.0)
            cr.fill()

        # Water droplets on banner (perfectly centered, zero wave shake)
        draw_water_drop(cr, bx + 52, banner_y, 26)
        draw_water_drop(cr, banner_front_x - 34, banner_y, 26)

        # TEXT: 100% stable, rock-solid vertical centering, ZERO jiggling/wobbling!
        text_x = bx + 24 + (bw - 24 - self.text_w) / 2
        text_y = banner_y - self.text_h / 2

        cr.save()
        # Crisp white background glow for high readability
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.9)
        cr.move_to(text_x, text_y + 1)
        PangoCairo.show_layout(cr, self.pango_layout)
        # Deep bold navy text
        cr.set_source_rgba(0.03, 0.18, 0.42, 1.0)
        cr.move_to(text_x, text_y)
        PangoCairo.show_layout(cr, self.pango_layout)
        cr.restore()

        cr.restore()

    # -------------------------------------------------------------------------
    # RIGHT TO LEFT (RTL) RENDERING (Plane faces left)
    # -------------------------------------------------------------------------
    def _render_rtl(self, cr, plane_x, base_y, elapsed, bobbing=True):
        bob = math.sin(elapsed * 1.2) * 5.0 if bobbing else 0.0
        pitch = -math.cos(elapsed * 1.2) * 0.02 if bobbing else 0.0
        cur_plane_y = base_y + bob

        for i in range(6):
            puff_phase = elapsed * 3.0 + i * 0.85
            px = plane_x + 125 + i * 22 + math.sin(puff_phase) * 2
            py = cur_plane_y + 8 + math.sin(puff_phase * 0.6) * 3
            r = 7 + i * 3.2
            a = max(0.0, 0.48 - i * 0.075)
            if a > 0:
                pat = cairo.RadialGradient(px - r * 0.3, py - r * 0.3, 1, px, py, r)
                pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, a * 1.2)
                pat.add_color_stop_rgba(0.7, 0.9, 0.96, 1.0, a)
                pat.add_color_stop_rgba(1.0, 0.8, 0.92, 1.0, 0.0)
                cr.set_source(pat)
                cr.arc(px, py, r, 0, 2 * math.pi)
                cr.fill()

        tail_x = plane_x + 122
        tail_y = cur_plane_y
        bridle_x = tail_x + 25
        banner_x = tail_x + self.cable_length
        banner_y = base_y + (math.sin(elapsed * 1.2 - 0.4) * 5.0 if bobbing else 0.0)

        cr.save()
        cr.set_source_rgba(0.2, 0.25, 0.3, 0.85)
        cr.set_line_width(1.8)
        cr.move_to(tail_x, tail_y - 10)
        cr.line_to(bridle_x, tail_y)
        cr.move_to(tail_x, tail_y + 8)
        cr.line_to(bridle_x, tail_y)
        cr.curve_to(bridle_x + 12, tail_y + 4, banner_x - 12, banner_y + 2, banner_x, banner_y)
        cr.stroke()
        cr.restore()

        self._render_banner_rtl(cr, banner_x, banner_y, elapsed)

        sparkle_phase = elapsed * 3.5
        s1 = 0.5 + 0.5 * math.sin(sparkle_phase)
        s2 = 0.5 + 0.5 * math.sin(sparkle_phase + 2.0)
        s3 = 0.5 + 0.5 * math.sin(sparkle_phase + 4.0)
        draw_sparkle(cr, banner_x + self.banner_width + 16, banner_y - 12, 7 + s1 * 2, 0.7 * s1 + 0.2)
        draw_sparkle(cr, banner_x + self.banner_width + 36, banner_y + 15, 6 + s2 * 2, 0.7 * s2 + 0.2)
        draw_sparkle(cr, banner_x + self.banner_width + 56, banner_y - 3, 8 + s3 * 2, 0.8 * s3 + 0.2)

        cr.save()
        cr.translate(plane_x, cur_plane_y)
        cr.rotate(pitch)
        self._render_plane_body(cr, elapsed)
        cr.restore()

    def _render_banner_rtl(self, cr, bx, banner_y, elapsed):
        bw = self.banner_width
        bh = self.banner_height
        by = banner_y - bh / 2

        steps = 36
        wave_freq = 0.25
        wave_speed = 2.8
        wave_amp = 2.0

        top_pts = []
        bot_pts = []
        for i in range(steps + 1):
            cx = bx + (bw * i / steps)
            w = math.sin(elapsed * wave_speed + i * wave_freq) * wave_amp
            top_pts.append((cx, by + w))
            bot_pts.append((cx, by + bh + w))

        cr.save()
        cr.new_path()
        cr.move_to(top_pts[0][0], top_pts[0][1])
        for pt in top_pts[1:]:
            cr.line_to(pt[0], pt[1])

        notch_x = bx + bw - 24
        mid_y = (top_pts[-1][1] + bot_pts[-1][1]) / 2
        cr.line_to(notch_x, mid_y)
        cr.line_to(bot_pts[-1][0], bot_pts[-1][1])

        for pt in reversed(bot_pts[:-1]):
            cr.line_to(pt[0], pt[1])
        cr.close_path()

        b_pat = cairo.LinearGradient(bx, by, bx, by + bh)
        b_pat.add_color_stop_rgba(0.0, 0.98, 0.99, 1.0, 0.97)
        b_pat.add_color_stop_rgba(0.5, 0.94, 0.97, 1.0, 0.97)
        b_pat.add_color_stop_rgba(1.0, 0.88, 0.93, 0.98, 0.97)
        cr.set_source(b_pat)
        cr.fill_preserve()

        cr.save()
        cr.clip_preserve()
        for i in range(steps):
            x1 = top_pts[i][0]
            x2 = top_pts[i + 1][0]
            slope = math.cos(elapsed * wave_speed + i * wave_freq)
            if slope > 0:
                cr.set_source_rgba(1.0, 1.0, 1.0, slope * 0.15)
            else:
                cr.set_source_rgba(0.0, 0.1, 0.3, -slope * 0.08)
            cr.rectangle(x1, by - 10, x2 - x1, bh + 20)
            cr.fill()
        cr.restore()

        cr.set_source_rgba(0.12, 0.45, 0.82, 0.95)
        cr.set_line_width(2.4)
        cr.stroke()

        cr.set_source_rgba(0.38, 0.24, 0.12, 1.0)
        cr.set_line_width(4.5)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(bx, top_pts[0][1] - 2)
        cr.line_to(bx, bot_pts[0][1] + 2)
        cr.stroke()

        for gy in [top_pts[0][1] + 6, bot_pts[0][1] - 6]:
            cr.arc(bx + 4, gy, 2.5, 0, 2 * math.pi)
            cr.set_source_rgba(0.85, 0.75, 0.2, 1.0)
            cr.fill()

        # Water droplets (stable)
        draw_water_drop(cr, bx + 28, banner_y, 26)
        draw_water_drop(cr, bx + bw - 46, banner_y, 26)

        # TEXT: 100% stable, zero wave shake
        text_x = bx + (bw - 20 - self.text_w) / 2 + 6
        text_y = banner_y - self.text_h / 2

        cr.save()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.9)
        cr.move_to(text_x, text_y + 1)
        PangoCairo.show_layout(cr, self.pango_layout)
        cr.set_source_rgba(0.03, 0.18, 0.42, 1.0)
        cr.move_to(text_x, text_y)
        PangoCairo.show_layout(cr, self.pango_layout)
        cr.restore()

        cr.restore()

    def _render_plane_body(self, cr, elapsed):
        """Draws plane body at local (0, 0) with nose at (0, 0) facing -X (left)."""
        # Landing Gear & Wheel
        cr.save()
        cr.set_source_rgba(0.2, 0.2, 0.25, 1.0)
        cr.set_line_width(2.5)
        cr.move_to(35, 12)
        cr.line_to(28, 28)
        cr.stroke()
        cr.arc(28, 28, 7, 0, 2 * math.pi)
        cr.set_source_rgba(0.15, 0.15, 0.18, 1.0)
        cr.fill_preserve()
        cr.set_source_rgba(0.05, 0.05, 0.05, 1.0)
        cr.set_line_width(1.2)
        cr.stroke()
        cr.arc(28, 28, 3, 0, 2 * math.pi)
        cr.set_source_rgba(0.85, 0.85, 0.9, 1.0)
        cr.fill()
        cr.restore()

        # Fuselage
        cr.new_path()
        cr.move_to(0, 0)
        cr.curve_to(6, -16, 28, -20, 60, -18)
        cr.curve_to(82, -16, 110, -8, 122, -3)
        cr.line_to(122, 3)
        cr.curve_to(110, 7, 85, 14, 55, 14)
        cr.curve_to(30, 14, 8, 12, 0, 0)
        cr.close_path()

        f_pat = cairo.LinearGradient(0, -20, 0, 20)
        f_pat.add_color_stop_rgba(0.0, 0.18, 0.62, 0.95, 1.0)
        f_pat.add_color_stop_rgba(0.4, 0.12, 0.48, 0.88, 1.0)
        f_pat.add_color_stop_rgba(1.0, 0.06, 0.32, 0.68, 1.0)
        cr.set_source(f_pat)
        cr.fill_preserve()
        cr.set_source_rgba(0.05, 0.2, 0.45, 1.0)
        cr.set_line_width(1.8)
        cr.stroke()

        # White Speed Stripe
        cr.save()
        cr.new_path()
        cr.move_to(5, 0)
        cr.curve_to(30, -3, 70, -3, 122, 0)
        cr.line_to(122, 4)
        cr.curve_to(70, 2, 30, 2, 5, 2)
        cr.close_path()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.92)
        cr.fill()
        cr.restore()

        # Cockpit & Aviator
        cr.save()
        cr.arc(46, -11, 10, math.pi, 2 * math.pi)
        cr.set_source_rgba(0.1, 0.1, 0.15, 1.0)
        cr.fill()
        cr.arc(46, -16, 6.5, 0, 2 * math.pi)
        cr.set_source_rgba(0.85, 0.55, 0.35, 1.0)
        cr.fill()
        cr.arc(46, -17, 7, math.pi * 0.7, math.pi * 2.1)
        cr.set_source_rgba(0.4, 0.22, 0.1, 1.0)
        cr.fill()
        cr.arc(42, -16, 3.2, 0, 2 * math.pi)
        cr.set_source_rgba(0.2, 0.8, 1.0, 0.9)
        cr.fill_preserve()
        cr.set_source_rgba(0.1, 0.1, 0.1, 1.0)
        cr.set_line_width(1.0)
        cr.stroke()
        cr.move_to(44, -16)
        cr.line_to(52, -15)
        cr.stroke()

        # Windshield
        cr.new_path()
        cr.move_to(34, -14)
        cr.curve_to(36, -24, 42, -26, 46, -26)
        cr.line_to(44, -18)
        cr.close_path()
        w_pat = cairo.LinearGradient(34, -26, 46, -14)
        w_pat.add_color_stop_rgba(0.0, 0.8, 0.98, 1.0, 0.85)
        w_pat.add_color_stop_rgba(1.0, 0.3, 0.6, 0.9, 0.4)
        cr.set_source(w_pat)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.8)
        cr.set_line_width(1.2)
        cr.stroke()
        cr.restore()

        # Tail Fin
        cr.new_path()
        cr.move_to(98, -6)
        cr.curve_to(106, -26, 114, -36, 122, -36)
        cr.curve_to(125, -36, 126, -33, 125, -28)
        cr.line_to(122, -3)
        cr.close_path()
        t_pat = cairo.LinearGradient(100, -36, 125, 0)
        t_pat.add_color_stop_rgba(0.0, 1.0, 0.35, 0.25, 1.0)
        t_pat.add_color_stop_rgba(1.0, 0.85, 0.15, 0.15, 1.0)
        cr.set_source(t_pat)
        cr.fill_preserve()
        cr.set_source_rgba(0.6, 0.1, 0.1, 1.0)
        cr.set_line_width(1.5)
        cr.stroke()

        # Elevator
        cr.new_path()
        cr.move_to(108, -2)
        cr.line_to(126, -9)
        cr.line_to(128, -6)
        cr.line_to(112, 1)
        cr.close_path()
        cr.set_source_rgba(0.9, 0.25, 0.2, 1.0)
        cr.fill()

        # Main Swept Wing
        cr.save()
        cr.new_path()
        cr.move_to(36, 1)
        cr.curve_to(48, -16, 68, -22, 78, -22)
        cr.line_to(84, -18)
        cr.curve_to(76, -14, 62, 0, 52, 6)
        cr.close_path()
        wing_pat = cairo.LinearGradient(36, -22, 84, 6)
        wing_pat.add_color_stop_rgba(0.0, 0.98, 0.99, 1.0, 1.0)
        wing_pat.add_color_stop_rgba(0.7, 0.88, 0.93, 1.0, 1.0)
        wing_pat.add_color_stop_rgba(1.0, 0.75, 0.82, 0.9, 1.0)
        cr.set_source(wing_pat)
        cr.fill_preserve()
        cr.set_source_rgba(0.1, 0.35, 0.6, 1.0)
        cr.set_line_width(1.5)
        cr.stroke()

        # Wing tip
        cr.new_path()
        cr.move_to(72, -21)
        cr.line_to(78, -22)
        cr.line_to(84, -18)
        cr.line_to(79, -16)
        cr.close_path()
        cr.set_source_rgba(1.0, 0.35, 0.25, 1.0)
        cr.fill()
        cr.restore()

        # Exhaust Pipe
        cr.save()
        cr.set_source_rgba(0.25, 0.25, 0.3, 1.0)
        cr.rectangle(18, 6, 8, 3)
        cr.fill()
        cr.restore()

        # Propeller Assembly
        cr.save()
        cr.new_path()
        cr.move_to(0, -6)
        cr.curve_to(-7, -4, -9, 0, -9, 0)
        cr.curve_to(-9, 0, -7, 4, 0, 6)
        cr.close_path()
        cr.set_source_rgba(1.0, 0.3, 0.2, 1.0)
        cr.fill_preserve()
        cr.set_source_rgba(0.6, 0.1, 0.1, 1.0)
        cr.set_line_width(1.2)
        cr.stroke()

        cr.save()
        cr.scale(0.35, 1.0)
        disc_pat = cairo.RadialGradient(-20, 0, 3, -20, 0, 32)
        disc_pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.6)
        disc_pat.add_color_stop_rgba(0.5, 0.85, 0.95, 1.0, 0.3)
        disc_pat.add_color_stop_rgba(0.85, 1.0, 0.8, 0.2, 0.4)
        disc_pat.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(disc_pat)
        cr.arc(-20, 0, 32, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

        prop_angle = elapsed * 45.0
        for angle_offset in [0, math.pi]:
            cr.save()
            cr.translate(-7, 0)
            cr.rotate(prop_angle + angle_offset)
            cr.scale(0.28, 1.0)
            cr.new_path()
            cr.arc(0, 16, 6, 0, 2 * math.pi)
            cr.set_source_rgba(0.2, 0.2, 0.25, 0.8)
            cr.fill()
            cr.arc(0, 24, 4, 0, 2 * math.pi)
            cr.set_source_rgba(1.0, 0.85, 0.1, 0.9)
            cr.fill()
            cr.restore()

        cr.restore()
