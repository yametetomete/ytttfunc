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
            out = out[:start] + clip_b[start : end + 1] + out[end + 1 :]
        else:
            out = out[:r] + clip_b[r] + out[r + 1 :]
    return out
