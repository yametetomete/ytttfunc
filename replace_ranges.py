def replace_ranges(clip_a, clip_b, ranges):
    """
    Replace frames from clip_a with clip_b. Inspired by ReplaceFramesSimple,
    but using text instead of perfectly useable native objects is stupid.

    ranges: List of integers (for single frames) or tuples (for frame ranges)
            to replace clip_a with clip_b. Ranges are inclusive.
    """
    out = clip_a
    for r in ranges:
        if type(r) is tuple:
            start, end = r
        else:
            start = r
            end = r
        tmp = clip_b[start : end + 1]
        if start != 0:
            tmp = out[: start] + tmp
        if end < out.num_frames - 1:
            tmp = tmp + out[end + 1 :]
        out = tmp
    return out
