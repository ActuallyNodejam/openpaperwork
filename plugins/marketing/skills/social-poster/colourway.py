#!/usr/bin/env python3
"""The three-stop tint, ported exactly from the old app's Engine recolour.

`motion recolour` tinted an approved anchor into a fair's colour through
its recolour service and one ffmpeg `lutrgb` chain.
That code left with the old app, so the chain is rebuilt here with the same
stops, the same midpoint rule and the same expressions, and it is applied the
same way the old app applied it: by ffmpeg, as one pass over the picture.

The chain reads each pixel's luma, so every tone keeps its place and only its
colour changes; the clip keeps its own frame count, duration and seam, because
the map is a pure function of each pixel. A still in is a still out.

    chain(color)   the ffmpeg filter, the old shape expression for expression
    filter_for()   the same chain with its output pixel format for a clip or a still

A light look, dark words on white paper, takes the colour another way (`wash_chain`):
the plate's white stays white and its darkest tone becomes the fair's colour itself,
so a pale campaign colour lands on the page as the brand chose it. The three-stop
ramp would push the same plate's mid greys to the colour at full voice, far deeper
than a pale poster carries.
"""

from __future__ import annotations

import colorsys

DARK_STOP_LUMINANCE = 0.10
LIGHT_STOP_LIFT = 0.88
MID_STOP_LIGHTNESS = 0.55
#: A wash never lays a colour darker than this luma: dark words must still read on it.
PALE_LUMA = 0.70

#: BT.601 luma weights — what ffmpeg's `format=gray` computes from RGB, so the
#: renormalisation cancels against the very number the filter derives.
_LUMA_R, _LUMA_G, _LUMA_B = 0.299, 0.587, 0.114


def parse_hex_color(color: str) -> tuple[float, float, float]:
    value = (color or "").strip()
    if not (len(value) == 7 and value[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in value[1:])):
        raise ValueError(f"colour must be #RRGGBB, not {color!r}")
    number = int(value[1:], 16)
    return (((number >> 16) & 255) / 255, ((number >> 8) & 255) / 255, (number & 255) / 255)


def _srgb_to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    return 0.2126 * _srgb_to_linear(rgb[0]) + 0.7152 * _srgb_to_linear(rgb[1]) + 0.0722 * _srgb_to_linear(rgb[2])


def darken_to_luminance(rgb: tuple[float, float, float], target: float) -> tuple[float, float, float]:
    """Scale a colour toward black until its relative luminance sits on `target`."""
    if relative_luminance(rgb) <= target:
        return rgb
    low, high = 0.0, 1.0
    for _ in range(32):
        mid = (low + high) / 2
        probe = (rgb[0] * mid, rgb[1] * mid, rgb[2] * mid)
        if relative_luminance(probe) > target:
            high = mid
        else:
            low = mid
    scale = (low + high) / 2
    return (rgb[0] * scale, rgb[1] * scale, rgb[2] * scale)


def stops(color: str) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    """(dark ground, mid stop, near-white lift) — the tint ramp's three stops."""
    rgb = parse_hex_color(color)
    dark = darken_to_luminance(rgb, DARK_STOP_LUMINANCE)
    hue, _lightness, saturation = colorsys.rgb_to_hls(*rgb)
    mid = colorsys.hls_to_rgb(hue, MID_STOP_LIGHTNESS, saturation)
    light = tuple(channel + (1.0 - channel) * LIGHT_STOP_LIFT for channel in rgb)
    return dark, (mid[0], mid[1], mid[2]), (light[0], light[1], light[2])


def _encoded_luma(rgb: tuple[float, float, float]) -> float:
    return _LUMA_R * rgb[0] + _LUMA_G * rgb[1] + _LUMA_B * rgb[2]


def chain(color: str) -> str:
    """The old app's tint chain, expression for expression.

    The ramp runs dark ground to the colour at full voice to a near-white lift,
    with the middle stop placed at its own luma, so footage keeps its tonal
    structure and every mid-tone carries the campaign colour instead of the grey
    between the two outer stops. Dividing by the ramp's own luma and multiplying
    by the source's puts the source's luma back, so the map is a pure recolour.
    """
    dark, mid, light = stops(color)
    luma = [_encoded_luma(dark), _encoded_luma(mid), _encoded_luma(light)]
    m = min(max(luma[1], luma[0] + 0.02), luma[2] - 0.02)

    def piecewise(low: float, middle: float, high: float) -> str:
        return (
            f"if(lt(val/255,{m:.6f}),"
            f"{low:.6f}+({middle - low:.6f})*(val/255)/{m:.6f},"
            f"{middle:.6f}+({high - middle:.6f})*(val/255-{m:.6f})/{1.0 - m:.6f})"
        )

    ramp_luma = piecewise(luma[0], luma[1], luma[2])

    def channel_expression(index: int) -> str:
        ramp = piecewise(dark[index], mid[index], light[index])
        return f"clip(({ramp})*(val/255)/max({ramp_luma},0.0039),0,1)*255"

    return (
        "format=gray,format=gbrp,"
        f"lutrgb=r='{channel_expression(0)}'"
        f":g='{channel_expression(1)}'"
        f":b='{channel_expression(2)}'"
    )


def wash_stop(color: str) -> tuple[float, float, float]:
    """The colour a wash lays at full strength: the fair's own, lifted toward white only when it is too deep for dark words."""
    rgb = parse_hex_color(color)
    luma = _encoded_luma(rgb)
    if luma >= PALE_LUMA:
        return rgb
    lift = (PALE_LUMA - luma) / (1.0 - luma)
    return (rgb[0] + (1.0 - rgb[0]) * lift, rgb[1] + (1.0 - rgb[1]) * lift, rgb[2] + (1.0 - rgb[2]) * lift)


def wash_chain(color: str) -> str:
    """White paper washed with the colour: white stays white, black becomes the colour, every grey sits between.

    A pure function of each pixel, like the ramp, so a closed loop stays closed and a still in is a still out.
    """
    stop = wash_stop(color)
    return "format=gray,format=gbrp,lutrgb=" + ":".join(
        f"{name}='({channel:.6f}+{1.0 - channel:.6f}*val/255)*255'" for name, channel in zip("rgb", stop))


def filter_for(color: str, *, still: bool = False, prefix: str = "", finish: str = "",
               keep: float = 0.0, saturation: float = 1.0, wash: bool = False) -> str:
    """The chain with the pixel format its output needs, after any framing steps.

    A clip lands on yuv420p, the composer's own profile. A still keeps full
    chroma, because halving it would change the colour the PNG carries. A look
    may carry a `finish` step — the brand measured it against the brand's own
    poster — and it runs last, over the recoloured picture.
    """
    steps = f"{prefix}," if prefix else ""
    tail = f",{finish}" if finish else ""
    out = "format=rgb24" if still else "format=yuv420p"
    tint = wash_chain(color) if wash else chain(color)
    if keep <= 0:
        return f"{steps}{tint}{tail},{out}"
    # A photo look keeps part of the photo's own colour (`keep`, softened by `saturation`):
    # the photo, its own colour at `keep`, is laid over the recoloured picture. Still a pure function of
    # each pixel, so a closed loop stays closed.
    # The split is fixed to full colour first: its two branches share one pixel format, and
    # the tint branchs grey step would otherwise turn the photos own branch grey as well.
    return (f"{steps}format=gbrp,split[njk_photo][njk_tint];[njk_tint]{tint}[njk_toned];"
            f"[njk_photo]eq=saturation={saturation:.3f},format=gbrp[njk_own];"
            f"[njk_own][njk_toned]blend=all_mode=normal:all_opacity={keep:.3f}{tail},{out}")
