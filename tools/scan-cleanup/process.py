import sys, json
import cv2
import numpy as np

SRC = "/tmp/sprechen-src/pdf"
OUT = "/tmp/sprechen-work/out"

def deskew_angle(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    s = 1200 / max(h, w)
    small = cv2.resize(gray, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape
    bw = cv2.adaptiveThreshold(small, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 18)
    bw = bw[int(sh * 0.08):int(sh * 0.92), int(sw * 0.08):int(sw * 0.92)]
    bh, bwid = bw.shape
    best, best_score = 0.0, -1
    for a in np.arange(-5, 5.001, 0.05):
        M = cv2.getRotationMatrix2D((bwid / 2, bh / 2), a, 1.0)
        r = cv2.warpAffine(bw, M, (bwid, bh), flags=cv2.INTER_NEAREST)
        prof = r.sum(axis=1).astype(np.float64)
        score = np.sum(np.diff(prof) ** 2)
        if score > best_score:
            best, best_score = a, score
    return float(best)

def rotate(img, angle):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

def homography(img, quad, frame):
    (tl, tr, br, bl) = [np.array(p, dtype=np.float64) for p in quad]
    bw = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    bh = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    ml, mr, mt, mb = frame
    W, H = int(ml + bw + mr), int(mt + bh + mb)
    dst = np.array([[ml, mt], [ml + bw, mt], [ml + bw, mt + bh], [ml, mt + bh]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype=np.float32), dst)
    return cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

def enhance(img):
    f = img.astype(np.float32) / 255.0
    h, w = f.shape[:2]
    mx0 = f.max(axis=2)
    bright = mx0 >= np.percentile(mx0, 85)
    paper_col = np.median(f[bright], axis=0)
    f = np.clip(f / np.maximum(paper_col[None, None, :], 0.05) * 0.9, 0, 1)
    s = 400 / max(h, w)
    small = cv2.resize(f, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    mx = small.max(axis=2); mn = small.min(axis=2)
    sat = (mx - mn) / (mx + 1e-6)
    paper = np.percentile(mx, 90)
    mask = ((mx > 0.80 * paper) & (sat < 0.10)).astype(np.float32)
    sigma = 0.06 * max(small.shape[:2])
    num = cv2.GaussianBlur(small * mask[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(mask, (0, 0), sigma)[..., None]
    bg = num / np.maximum(den, 1e-4)
    gp = np.median(small[mask > 0], axis=0)
    wgt = np.clip(den / 0.25, 0, 1)
    bg = bg * wgt + gp[None, None, :] * (1 - wgt)
    bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_CUBIC)
    out = f / np.maximum(bg, 0.05)
    out = np.clip((out - 0.06) / (0.94 - 0.06), 0, 1) ** 1.25
    blur = cv2.GaussianBlur(out, (0, 0), 1.3)
    out = np.clip(out + 0.7 * (out - blur), 0, 1)
    return (out * 255 + 0.5).astype(np.uint8)

def grid(img, path):
    h, w = img.shape[:2]
    s = 1000 / max(h, w)
    sm = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    sh, sw = sm.shape[:2]
    for i in range(1, 40):
        x = int(sw * i / 40); y = int(sh * i / 40)
        col = (0, 0, 255) if i % 4 == 0 else (255, 160, 0)
        cv2.line(sm, (x, 0), (x, sh), col, 1); cv2.line(sm, (0, y), (sw, y), col, 1)
        if i % 4 == 0:
            cv2.putText(sm, str(int(i * 2.5)), (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
            cv2.putText(sm, str(int(i * 2.5)), (2, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
    cv2.imwrite(path, sm, [cv2.IMWRITE_JPEG_QUALITY, 85])

if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    specs = json.load(open(sys.argv[1]))
    for sp in specs:
        img = cv2.imread(f"{SRC}/p-{sp['src']}.png", cv2.IMREAD_COLOR)
        if "quad" in sp:
            img = homography(img, sp["quad"], sp["frame"]); ang = None
        else:
            ang = sp.get("angle")
            if ang is None:
                ang = deskew_angle(img)
            img = rotate(img, ang)
        img = enhance(img)
        h, w = img.shape[:2]
        for (x0, y0, x1, y1) in sp.get("paint", []):
            img[int(h * y0 / 100):int(h * y1 / 100), int(w * x0 / 100):int(w * x1 / 100)] = 255
        if "crop" in sp:
            x0, y0, x1, y1 = sp["crop"]
            img = img[int(h * y0 / 100):int(h * y1 / 100), int(w * x0 / 100):int(w * x1 / 100)]
        cv2.imwrite(f"{OUT}/{sp['id']}_full.png", img)
        grid(img, f"{OUT}/{sp['id']}_grid.jpg")
        print(sp["id"], sp["src"], "angle", None if ang is None else round(ang, 2), img.shape)
