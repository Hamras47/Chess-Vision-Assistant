import numpy as np
import mss


def square_crop(image):
    """Return the largest centered square from a one-time user selection."""
    if image is None or image.ndim != 3:
        raise ValueError("Selected image is invalid")
    height, width = image.shape[:2]
    size = min(height, width)
    if size < 64:
        raise ValueError("Selected board is too small")
    x = (width - size) // 2
    y = (height - size) // 2
    return image[y:y + size, x:x + size].copy()


class ScreenCapture:
    """Take one frozen image per physical monitor when Scan/Rescan begins."""

    def monitor_frames(self):
        with mss.mss() as s:
            return [(np.array(s.grab(m))[:, :, :3],dict(left=m['left'],top=m['top'],width=m['width'],height=m['height'])) for m in s.monitors[1:]]

    def region(self, physical):
        """Capture exactly the already DPI-mapped physical rectangle."""
        if physical['width'] < 64 or physical['height'] < 64:
            raise ValueError("Selected board is too small")
        with mss.mss() as capture:
            return np.array(capture.grab(physical))[:, :, :3]


def validated_board_crop(image):
    crop = square_crop(image)
    if crop.shape[2] != 3 or crop.dtype != np.uint8:
        raise ValueError("Invalid screenshot format")
    # A chessboard has substantial spatial variation. Per-channel deviation
    # avoids treating a uniform colored desktop as a valid board.
    if float(np.std(crop.astype(np.float32), axis=(0, 1)).max()) < 3.0:
        raise ValueError("Screenshot is blank or near-uniform")
    return crop
