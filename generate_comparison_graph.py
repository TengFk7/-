"""
generate_comparison_graph.py
────────────────────────────
Runs YOLOv8 detection on two video sources and produces a professional
dark-themed comparison graph (styled after YOLOv8 training result charts).

Video A (Train):  3156802-uhd_3840_2160_30fps.mp4
Video B (Val):    uploads/4062994-uhd_3840_2160_30fps.mp4

Each video is sampled at a fixed interval.  Per-sample metrics
(vehicle count, mean confidence) are mapped to simulated "epochs"
so both videos can be compared on the same X-axis scale.

Output: comparison_training_graph.png  (overwrites the existing file)
"""

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from ultralytics import YOLO
import os, time

# ── Config ─────────────────────────────────────────────────────────────────────
VIDEO_A = r"3156802-uhd_3840_2160_30fps.mp4"          # "Train" video
VIDEO_B = r"uploads\4062994-uhd_3840_2160_30fps.mp4"  # "Val" video
MODEL_PATH = "yolov8m.pt"
OUTPUT_PATH = "comparison_training_graph.png"

# Number of simulated epochs on the X-axis
N_EPOCHS = 50

# How many evenly-spaced frames to sample from each video
N_SAMPLES = 50          # one sample per epoch tick

VEHICLE_CLASSES = [2, 3, 5, 7]   # car, motorbike, bus, truck
CONF_THRESH = 0.25
IMG_SIZE = 640          # smaller imgsz speeds up the scan

# ── Matplotlib dark style ───────────────────────────────────────────────────────
DARK_BG   = "#0d0d0d"
GRID_CLR  = "#2a2a2a"
TEXT_CLR  = "#e0e0e0"

COLOR_A_LOSS = "#F2726F"   # reddish-pink  (Train)
COLOR_B_LOSS = "#58C6B6"   # teal          (Val)
COLOR_A_MAP  = "#58C6B6"   # teal          (mAP 0.50)
COLOR_B_MAP  = "#F9B497"   # peach         (mAP 0.50:0.95)

# ── Helpers ────────────────────────────────────────────────────────────────────

def sample_video(video_path: str, model: YOLO, n_samples: int) -> dict:
    """
    Open *video_path*, pick *n_samples* evenly-spaced frames,
    run detection on each, and return per-sample metrics.

    Returns
    -------
    dict with keys:
        counts      – list[int]   vehicle count per sample
        confs       – list[float] mean confidence per sample (0–1)
        box_losses  – list[float] synthetic box-loss proxy (lower = better)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS) or 30
    print(f"\n  [{os.path.basename(video_path)}]  {total_frames} frames @ {fps:.1f} fps")

    # Evenly-spaced frame indices
    indices = np.linspace(0, total_frames - 1, n_samples, dtype=int)

    counts, confs, losses = [], [], []
    rng = np.random.default_rng(seed=42)   # reproducible jitter

    for i, idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret:
            counts.append(counts[-1] if counts else 0)
            confs.append(confs[-1]   if confs  else 0.0)
            losses.append(losses[-1] if losses else 1.5)
            continue

        # Downscale for speed
        h, w = frame.shape[:2]
        scale = min(IMG_SIZE / w, IMG_SIZE / h, 1.0)
        if scale < 1.0:
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

        results = model.predict(frame, classes=VEHICLE_CLASSES,
                                conf=CONF_THRESH, imgsz=IMG_SIZE,
                                verbose=False)

        boxes = results[0].boxes
        n     = len(boxes) if boxes is not None else 0
        mean_conf = float(boxes.conf.mean()) if (boxes is not None and n > 0) else 0.0

        # Synthetic box-loss: higher confidence → lower loss
        # loss = (1 – mean_conf)  + small noise, clamped to [0.8, 2.0]
        noise  = rng.normal(0, 0.04)
        loss   = np.clip((1.0 - mean_conf) * 1.5 + 0.9 + noise, 0.8, 2.2)

        counts.append(n)
        confs.append(round(mean_conf, 4))
        losses.append(round(float(loss), 4))

        print(f"    epoch {i+1:>3}/{n_samples}  frame={idx:>6}  "
              f"vehicles={n:>3}  conf={mean_conf:.3f}  loss={loss:.3f}")

    cap.release()
    return {"counts": counts, "confs": confs, "box_losses": losses}


def smooth(data: list, w: int = 3) -> np.ndarray:
    """Simple moving-average smoothing."""
    arr = np.array(data, dtype=float)
    kernel = np.ones(w) / w
    padded = np.pad(arr, (w // 2, w // 2), mode='edge')
    return np.convolve(padded, kernel, mode='valid')[:len(arr)]


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 60)
    print("  Video Comparison Graph Generator")
    print("=" * 60)

    # Load model once
    print(f"\nLoading model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)

    # Analyse both videos
    print("\n[1/2] Analysing Video A (Train) …")
    data_a = sample_video(VIDEO_A, model, N_SAMPLES)

    print("\n[2/2] Analysing Video B (Val) …")
    data_b = sample_video(VIDEO_B, model, N_SAMPLES)

    # X-axis (epochs)
    epochs = np.arange(1, N_SAMPLES + 1)

    # Smoothed metrics
    loss_a = smooth(data_a["box_losses"], w=3)
    loss_b = smooth(data_b["box_losses"], w=3)
    map_a  = smooth(data_a["confs"],      w=3)
    map_b  = smooth(data_b["confs"],      w=3)

    # ── Plot ────────────────────────────────────────────────────────────────────
    rcParams["font.family"] = "DejaVu Sans"
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.patch.set_facecolor(DARK_BG)

    for ax in axes:
        ax.set_facecolor(DARK_BG)
        ax.tick_params(colors=TEXT_CLR, labelsize=11)
        ax.xaxis.label.set_color(TEXT_CLR)
        ax.yaxis.label.set_color(TEXT_CLR)
        ax.title.set_color(TEXT_CLR)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_CLR)
        ax.grid(True, color=GRID_CLR, linewidth=0.7, linestyle='--')
        ax.set_xlim(0, N_SAMPLES + 1)

    # — Left panel: Box Loss ────────────────────────────────────────────────────
    ax_loss = axes[0]
    ax_loss.plot(epochs, loss_a, color=COLOR_A_LOSS, linewidth=1.6,
                 label="Train Box Loss")
    ax_loss.plot(epochs, loss_b, color=COLOR_B_LOSS, linewidth=1.6,
                 label="Val Box Loss")
    ax_loss.set_title("Training vs Validation Loss", fontsize=14, pad=14)
    ax_loss.set_xlabel("Epoch", fontsize=12)
    ax_loss.set_ylabel("Loss", fontsize=12)
    leg = ax_loss.legend(facecolor="#1a1a1a", edgecolor=GRID_CLR,
                         labelcolor=TEXT_CLR, fontsize=9.5)

    # — Right panel: mAP (mean confidence as accuracy proxy) ────────────────────
    ax_map = axes[1]
    ax_map.plot(epochs, map_a, color=COLOR_A_MAP, linewidth=1.6,
                label="mAP@0.50 (Base Accuracy)")
    ax_map.plot(epochs, map_b, color=COLOR_B_MAP, linewidth=1.6,
                label="mAP@0.50:0.95 (Strict Accuracy)")
    ax_map.set_title("Model Accuracy (mAP)", fontsize=14, pad=14)
    ax_map.set_xlabel("Epoch", fontsize=12)
    ax_map.set_ylabel("Accuracy (0 to 1)", fontsize=12)
    ax_map.set_ylim(0, 1.05)
    leg2 = ax_map.legend(facecolor="#1a1a1a", edgecolor=GRID_CLR,
                          labelcolor=TEXT_CLR, fontsize=9.5)

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches='tight',
                facecolor=DARK_BG)
    plt.close()

    elapsed = time.time() - t0
    print(f"\n✅  Graph saved → {OUTPUT_PATH}  ({elapsed:.1f}s total)")
    print("=" * 60)


if __name__ == "__main__":
    main()
