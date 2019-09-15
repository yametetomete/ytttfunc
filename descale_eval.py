#!/usr/bin/env python3

import vapoursynth as vs
import vsutil
import sys

from functools import partial
from typing import List

from kagefunc import get_descale_filter, mask_descale
from nnedi3_rpow2 import nnedi3_rpow2

core = vs.core


def get_scale_filter(kernel: str, **kwargs):
    """
    kgf.get_descale_filter but for core.resize
    """
    filters = {
        "bilinear": (lambda **kwargs: core.resize.Bilinear),
        "spline16": (lambda **kwargs: core.resize.Despline16),
        "spline36": (lambda **kwargs: core.resize.Despline36),
        "bicubic": (
            lambda b, c, **kwargs: partial(
                core.resize.Bicubic, filter_param_a=b, filter_param_b=c
            )
        ),
        "lanczos": (
            lambda taps, **kwargs: partial(
                core.resize.Lanczos, filter_param_a=taps
            )
        ),
    }
    return filters[kernel](**kwargs)


def mark_descale(
    clip: vs.VideoNode,
    height: int,
    kernel: str = "bicubic",
    b: float = 1 / 3,
    c: float = 1 / 3,
    taps: int = 5,
    debug: bool = False,
) -> vs.VideoNode:
    """
    Evaluates PlaneStats for a rescaled clip vs the original
    only operates on luma for now
    """

    y = vsutil.get_y(clip)
    descale = get_descale_filter(kernel, b=b, c=c, taps=taps)(
        y, vsutil.get_w(height), height
    )
    rescale = get_scale_filter(kernel, b=b, c=c, taps=taps)(
        descale, clip.width, clip.height, format=y.format
    )
    mask = core.std.Expr([y, rescale], "x y - abs dup 0.015 > swap 0 ?")
    mask = mask.std.PlaneStats()

    def copy_scale_error(n, f):
        f_out = f[0].copy()
        f_out.props["ScaleError"] = f[1].props.PlaneStatsAverage
        return f_out

    descale = core.std.ModifyFrame(
        clip=descale, clips=[descale, mask], selector=copy_scale_error
    )

    def write_scale_error(n, f, clip):
        return clip.text.Text(f"{f.props.ScaleError:.2e}")

    if debug:
        descale = core.std.FrameEval(
            descale, partial(write_scale_error, clip=descale), prop_src=descale
        )

    return descale


def descale_range(
    clip: vs.VideoNode,
    heights: List[int],
    target_height: int = None,
    kernel: str = "bicubic",
    b: float = 1 / 3,
    c: float = 1 / 3,
    taps: int = 5,
    threshold: float = 7e-6,
    mask_detail: bool = False,
    debug: bool = False,
):
    """
    Find the descaled frame with the lowest error given filter parameters and
    a set of heights and a threshold. If no descaled frame has a lower error
    than the threshold, uses the source frame.
    Resizes everything based on target_height.
    Uses kagefunc's mask_descale for optional detail masking.
    """

    def lazy_scale(clip, target_height):
        if clip.height < target_height:
            clip = nnedi3_rpow2(clip)
        return clip.resize.Spline36(
            vsutil.get_w(target_height), target_height, format=clip.format
        )

    clip = clip.resize.Point(
        format=clip.format.replace(bits_per_sample=32, sample_type=vs.FLOAT)
    )
    orig = clip
    descale = [
        mark_descale(
            clip, height=x, kernel=kernel, b=b, c=c, taps=taps, debug=debug
        )
        for x in heights
    ]
    upscale = [
        get_scale_filter(kernel=kernel, b=b, c=c, taps=taps)(
            x, orig.width, orig.height, format=orig.format
        )
        for x in descale
    ]

    if target_height is None:
        target_height = clip.height
    else:
        clip = lazy_scale(clip, target_height)

    def select_min_error(
        n, f, clip, descale, threshold, debug, mask_detail, upscale, orig
    ):
        min_index = f.index(min(f, key=lambda x: x.props.ScaleError))
        if f[min_index].props.ScaleError < threshold:
            d = descale[min_index]

            if mask_detail:
                d = mask_descale(orig, descale[min_index], upscale[min_index])

            rescale = lazy_scale(d, target_height)

            if debug:
                rescale = rescale.text.Text(
                    f"{descale[min_index].height}", alignment=9
                )

            return rescale

        else:
            if debug:
                clip = clip.text.Text(f"{clip.height}", alignment=9)
                clip = clip.text.Text(
                    f"{descale[min_index].height},"
                    f"{f[min_index].props.ScaleError:.2e}"
                )
            return clip

    return core.std.FrameEval(
        clip,
        partial(
            select_min_error,
            clip=clip,
            descale=descale,
            threshold=threshold,
            debug=debug,
            mask_detail=mask_detail,
            upscale=upscale,
            orig=orig,
        ),
        prop_src=descale,
    )


def main():
    # TODO: make this not useless
    src = core.ffms2.Source(sys.argv[1])
    descaled = mark_descale(src, 872)
    # descaled = eval_descale(src, marked)

    def print_err(n, f, clip):
        print(f"{f.props.ScaleError}")
        return clip

    descaled = core.std.FrameEval(
        descaled, partial(print_err, clip=descaled), prop_src=descaled
    )

    for i in range(len(descaled)):
        descaled.get_frame_async(i)


if __name__ == "__main__":
    main()
