import random


def layout(num, count):
    rng = random.Random(int(num) * 7919)
    slots = [0, 1, 2, 0, 1, 2]
    rng.shuffle(slots)
    out = []
    for k in range(count):
        perm = [0, 1]
        rng.shuffle(perm)
        out.append((slots[k % 6], perm))
    return out


def order(right, wrong, pos, perm):
    opts = [wrong[perm[0]], wrong[perm[1]]]
    opts.insert(pos, right)
    return opts


def player(num, count):
    prev = [p for p, _ in player(f"{int(num) - 1:02d}", count)] if int(num) > 1 else None
    for k in range(1, 20):
        out = layout(str(int(num) + 100 * k), count)
        if [p for p, _ in out] != prev:
            return out
    return out
