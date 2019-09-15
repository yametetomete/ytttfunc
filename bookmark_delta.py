"""
display frames since last bookmark for easier reusable scenefiltering
stolen from b6boost in weeb autism
"""

import vapoursynth as vs

core = vs.core


def load_bookmarks(filename):
    with open(filename) as f:
        bookmarks = [int(i) for i in f.read().split(", ")]

        if bookmarks[0] != 0:
            bookmarks.insert(0, 0)

    return bookmarks


def frames_from_bookmark(n, clip, bookmarks):
    for i, bookmark in enumerate(bookmarks):
        frames_since = n - bookmark

        if frames_since >= 0 and i + 1 >= len(bookmarks):
            result = frames_since
        elif frames_since >= 0 and n - bookmarks[i + 1] < 0:
            result = frames_since
            break

    return core.text.Text(clip, result)
