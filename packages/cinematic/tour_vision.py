#!/usr/bin/env python3
"""
Vision 5D — AI Photo Tour Director (TourVision port, local mode)

Transforms a set of static property photos into a polished cinematic
walkthrough video using ONLY local tooling (ffmpeg). This is the "option B"
integration: the classification logic is ported from TourVision
(gemini room-type labelling → grouping → smart scene selection), and the
video generation is implemented with ffmpeg Ken-Burns pan/zoom + xfade
crossfade stitching instead of a cloud video model (Veo).

Design rules (per V5D architecture reset):
  * NO duplicate pipelines — reuses packages.ai.ProviderAdapter.call_vision
    for classification and the existing ffmpeg toolchain for encoding.
  * Output flows through DurableArtifactRef in the caller, not here.
  * Fully local: produces a real MP4 with zero cloud video dependency.

Usage (CLI):
  python -m packages.cinematic.tour_vision IMG1 IMG2 ... --out DIR \
      --duration 45 --transition 1.2
"""
import os, sys, json, time, subprocess, tempfile, shutil, re, math
from dataclasses import dataclass, field
from typing import Optional

# ═══════════════════════ CONFIG ═══════════════════════
RES_W, RES_H = 1920, 1080
FPS = 30

# Veo3 API (third-party OpenAI-style wrapper over Google Veo 3.1)
VEO_BASE_URL = os.environ.get("VEO_BASE_URL", "https://veo3api.com")
VEO_MODEL_DEFAULT = os.environ.get("VEO_MODEL", "veo3-fast")  # veo3-fast (25cr) | veo3 (180cr)

# Preferred shot ordering — exterior / entry / lobby first (TourVision behaviour).
PRIORITY_KEYWORDS = ["exterior", "lobby", "entrance", "entree", "facade", "front", "pool", "parking", "garden"]


@dataclass
class TourClip:
    """A single room/scene clip produced from one or more images."""
    label: str
    image_paths: list
    clip_path: str
    duration_s: float


class VeoVideoGenerator:
    """Veo 3.1 video synthesis via the veo3api.com REST API.

    Async generate → poll feed → download. Uses Bearer auth. Cost:
    veo3-fast = 25 credits ($0.25), veo3 = 180 credits ($1.80) per clip.
    """

    def __init__(self, api_key: str, base_url: str = None, model: str = None):
        if not api_key:
            raise ValueError("VEO_API_KEY is required for Veo video generation")
        self.api_key = api_key
        self.base_url = (base_url or VEO_BASE_URL).rstrip("/")
        self.model = model or VEO_MODEL_DEFAULT

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def submit(self, prompt: str, image_urls: list = None,
               aspect_ratio: str = "16:9", watermark: str = None) -> str:
        """Submit a generation task. Returns task_id."""
        import httpx
        body = {"prompt": prompt, "model": self.model}
        if aspect_ratio:
            body["aspect_ratio"] = aspect_ratio
        if image_urls:
            body["image_urls"] = image_urls
        if watermark is not None:
            body["watermark"] = watermark

        url = f"{self.base_url}/generate"
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=body, headers=self._auth_headers())
        if resp.status_code != 200:
            raise RuntimeError(f"Veo submit failed ({resp.status_code}): {resp.text[:300]}")
        data = resp.json()
        task_id = (data.get("data") or {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"Veo submit returned no task_id: {resp.text[:300]}")
        return task_id

    def poll(self, task_id: str, timeout_s: int = 600, interval_s: int = 10) -> dict:
        """Poll /feed until COMPLETED or FAILED. Returns the feed data dict."""
        import httpx
        url = f"{self.base_url}/feed"
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            with httpx.Client(timeout=60) as client:
                resp = client.get(url, params={"task_id": task_id}, headers=self._auth_headers())
            if resp.status_code != 200:
                raise RuntimeError(f"Veo feed failed ({resp.status_code}): {resp.text[:300]}")
            data = (resp.json() or {}).get("data") or {}
            status = str(data.get("status", "")).upper()
            if status == "COMPLETED":
                return data
            if status in ("FAILED", "ERROR", "CANCELLED"):
                raise RuntimeError(f"Veo task {task_id} ended with status {status}: {json.dumps(data)[:300]}")
            time.sleep(interval_s)
        raise TimeoutError(f"Veo task {task_id} timed out after {timeout_s}s (last status: {status})")

    def download(self, video_url: str, dest_path: str) -> str:
        """Download a generated video to dest_path."""
        import httpx
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            resp = client.get(video_url)
        if resp.status_code != 200:
            raise RuntimeError(f"Veo download failed ({resp.status_code}): {resp.text[:200]}")
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    def generate(self, prompt: str, dest_path: str, image_urls: list = None,
                 aspect_ratio: str = "16:9", watermark: str = None,
                 timeout_s: int = 600) -> dict:
        """Submit → poll → download. Returns {path, task_id, video_url, status}."""
        task_id = self.submit(prompt, image_urls=image_urls,
                              aspect_ratio=aspect_ratio, watermark=watermark)
        data = self.poll(task_id, timeout_s=timeout_s)
        video_urls = data.get("response") or data.get("videos") or []
        if not video_urls:
            raise RuntimeError(f"Veo task {task_id} completed with no video URL: {json.dumps(data)[:300]}")
        video_url = video_urls[0]
        self.download(video_url, dest_path)
        return {"path": dest_path, "task_id": task_id, "video_url": video_url,
                "status": data.get("status"), "model": self.model}


class TourVisionDirector:
    """Photos → grouped, labelled, stitched cinematic tour video (local ffmpeg)."""

    def __init__(self, adapter=None, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe"):
        self.adapter = adapter          # Optional ProviderAdapter for classification
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe

    # ────────────────────────────────────────────────────────
    # CLASSIFICATION (TourVision port)
    # ────────────────────────────────────────────────────────
    def classify(self, image_path: str) -> str:
        """Return a single room-type label for an image.

        Tries the configured vision provider first. On any failure (no key,
        network, provider down) falls back to a filename-derived label so the
        pipeline still produces a tour locally.
        """
        label = None
        if self.adapter is not None:
            try:
                prompt = (
                    "Identify the primary subject or location in this photo. "
                    "Return ONLY a single lowercase label using underscores for "
                    "spaces (e.g. living_room, kitchen, bedroom, bathroom, exterior, "
                    "lobby, pool, office). No adjectives, no punctuation."
                )
                result = self.adapter.call_vision(image_path, prompt)
                parsed = result.get("parsed", {}) if isinstance(result, dict) else {}
                text = ""
                if isinstance(parsed, dict):
                    text = parsed.get("analysis", "") or parsed.get("label", "") or ""
                text = str(text).strip().lower()
                # Strip markdown fences / quotes / stray punctuation
                text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
                text = re.sub(r"[^a-z_]", "", text)
                if text and len(text) <= 40:
                    label = text
            except Exception as e:
                label = None  # fall through to filename heuristic

        if not label:
            label = self._label_from_filename(image_path)
        return label

    @staticmethod
    def _label_from_filename(image_path: str) -> str:
        base = os.path.splitext(os.path.basename(image_path))[0].lower()
        for kw in ["bedroom", "kitchen", "living", "bathroom", "dining", "lobby",
                   "entrance", "exterior", "pool", "office", "hallway", "garden",
                   "parking", "laundry", "balcony", "facade"]:
            if kw in base:
                return kw
        # Fall back to a stable scene name from the filename
        clean = re.sub(r"[^a-z0-9]+", "_", base).strip("_") or "scene"
        return f"scene_{clean}"

    # ────────────────────────────────────────────────────────
    # GROUPING
    # ────────────────────────────────────────────────────────
    @staticmethod
    def group_images(image_paths: list) -> dict:
        """Bucket images by label, preserving insertion order."""
        groups = {}
        for p in image_paths:
            groups.setdefault(p, None)
        return groups

    def build_groups(self, image_paths: list) -> dict:
        """Classify each image and group by label (ordered)."""
        groups = {}
        for p in image_paths:
            label = self.classify(p)
            groups.setdefault(label, []).append(p)
        return groups

    @staticmethod
    def order_labels(labels: list) -> list:
        """Exterior/lobby/entrance first, then the rest alphabetically."""
        def key(label):
            l = label.lower()
            prio = 0 if any(k in l for k in PRIORITY_KEYWORDS) else 1
            return (prio, l)
        return sorted(labels, key=key)

    # ────────────────────────────────────────────────────────
    # CLIP GENERATION (ffmpeg Ken Burns)
    # ────────────────────────────────────────────────────────
    def _normalize_image(self, src: str, dst: str):
        """Center-crop to 16:9 and resize to 1920x1080 using PIL."""
        try:
            from PIL import Image
        except ImportError:
            shutil.copy2(src, dst)
            return
        with Image.open(src) as im:
            im = im.convert("RGB")
            w, h = im.size
            target_ratio = RES_W / RES_H
            ratio = w / h
            if ratio > target_ratio:      # too wide → crop width
                new_w = int(h * target_ratio)
                x0 = (w - new_w) // 2
                box = (x0, 0, x0 + new_w, h)
            else:                          # too tall → crop height
                new_h = int(w / target_ratio)
                y0 = (h - new_h) // 2
                box = (0, y0, w, y0 + new_h)
            im = im.crop(box).resize((RES_W, RES_H), Image.LANCZOS)
            im.save(dst, "JPEG", quality=92)

    def _ken_burns_clip(self, normalized_img: str, out_path: str,
                        duration_s: float, motion: str = "zoom_in") -> None:
        """Produce a pan/zoom clip from a still using the zoompan filter.

        motion: "zoom_in" | "zoom_out" | "pan_right" | "pan_left"
        """
        total_frames = max(2, int(round(duration_s * FPS)))

        # Deterministic zoompan expressions driven by the output frame counter `on`.
        if motion == "zoom_out":
            z_expr = "max(1.0, 1.20 - 0.0008*on)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif motion == "pan_right":
            z_expr = "1.15"
            x_expr = "(iw-iw/zoom)*on/{N}".format(N=total_frames)
            y_expr = "ih/2-(ih/zoom/2)"
        elif motion == "pan_left":
            z_expr = "1.15"
            x_expr = "(iw-iw/zoom)*(1-on/{N})".format(N=total_frames)
            y_expr = "ih/2-(ih/zoom/2)"
        else:  # zoom_in (default)
            z_expr = "min(1.20, 1.0 + 0.0008*on)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"

        vf = (
            "zoompan=z='{z}':x='{x}':y='{y}':d={N}:s={w}x{h}:fps={fps}"
            .format(z=z_expr, x=x_expr, y=y_expr, N=total_frames,
                    w=RES_W, h=RES_H, fps=FPS)
        )

        cmd = [
            self.ffmpeg, "-y", "-loglevel", "error",
            "-i", normalized_img,
            "-vf", vf,
            "-frames:v", str(total_frames),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p",
            out_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)

    def _generate_clip(self, label: str, image_paths: list, out_dir: str,
                       duration_s: float, motion: str) -> str:
        """Generate a single labelled clip. Multi-image rooms use the first
        two images crossfaded together; single-image rooms are one Ken Burns shot."""
        safe = re.sub(r"[^a-z0-9_]+", "_", label.lower()).strip("_") or "scene"
        clip_path = os.path.join(out_dir, f"clip_{safe}.mp4")

        # Normalize up to 2 images for this scene
        images = image_paths[:2]
        norm_imgs = []
        for i, img in enumerate(images):
            norm = os.path.join(out_dir, f"_{safe}_norm{i}.jpg")
            self._normalize_image(img, norm)
            norm_imgs.append(norm)

        if len(norm_imgs) == 1:
            self._ken_burns_clip(norm_imgs[0], clip_path, duration_s, motion)
        else:
            # Crossfade two Ken Burns shots of half-duration each.
            half = duration_s / 2.0
            a = os.path.join(out_dir, f"_{safe}_a.mp4")
            b = os.path.join(out_dir, f"_{safe}_b.mp4")
            self._ken_burns_clip(norm_imgs[0], a, half + 0.6, motion)
            self._ken_burns_clip(norm_imgs[1], b, half + 0.6,
                                 "pan_left" if motion == "zoom_in" else "zoom_out")
            self._xfade([a, b], clip_path, 0.6)

        # Cleanup temp normalised images
        for n in norm_imgs:
            if os.path.exists(n):
                os.remove(n)
        for t in (a, b) if len(norm_imgs) > 1 else ():
            if os.path.exists(t):
                os.remove(t)
        return clip_path

    # ────────────────────────────────────────────────────────
    # STITCHING (ffmpeg xfade)
    # ────────────────────────────────────────────────────────
    def _xfade(self, clip_paths: list, out_path: str, transition_dur: float) -> None:
        """Concatenate clips with xfade crossfade transitions."""
        n = len(clip_paths)
        if n == 1:
            shutil.copy2(clip_paths[0], out_path)
            return

        inputs = []
        for c in clip_paths:
            inputs += ["-i", c]

        # Probe durations to compute offsets
        durs = [self._probe_duration(c) for c in clip_paths]

        # Build the filter graph: sequential xfade
        # offset_k = cumulative_duration_before_k - k*transition
        filter_parts = []
        prev = "[0:v]"
        cum = 0.0
        for k in range(n - 1):
            cum += durs[k]
            offset = cum - (k + 1) * transition_dur
            if offset <= 0:
                offset = 0.05
            next_label = f"[v{k}]"
            filter_parts.append(
                f"{prev}[{k+1}:v]xfade=transition=fade:duration={transition_dur:.3f}:offset={offset:.3f}{next_label}"
            )
            prev = next_label

        filter_complex = ";".join(filter_parts)
        cmd = [
            self.ffmpeg, "-y", "-loglevel", "error",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", prev,
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            out_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)

    def _probe_duration(self, path: str) -> float:
        try:
            cmd = [self.ffprobe, "-v", "quiet", "-print_format", "json",
                   "-show_format", path]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            data = json.loads(out.stdout)
            return float(data.get("format", {}).get("duration", 0))
        except Exception:
            return 5.0

    # ────────────────────────────────────────────────────────
    # MAIN PIPELINE
    # ────────────────────────────────────────────────────────
    def generate(self, image_paths: list, out_dir: str,
                 target_duration: float = 45.0, transition_dur: float = 1.2,
                 classify: bool = True) -> dict:
        """Run the full photo → tour-video pipeline.

        Returns a dict with clip list, final video path, thumb path, and stats.
        """
        os.makedirs(out_dir, exist_ok=True)

        image_paths = [p for p in image_paths if os.path.exists(p)]
        if not image_paths:
            raise ValueError("No valid image paths provided")

        # 1. Classify + group
        if classify:
            groups = self.build_groups(image_paths)
        else:
            groups = {"scene": image_paths}

        ordered_labels = self.order_labels(list(groups.keys()))

        # 2. Duration math (TourVision formula)
        num_scenes = max(1, len(ordered_labels))
        total_transition = (num_scenes - 1) * transition_dur
        per_clip = (target_duration + total_transition) / num_scenes

        # 3. Generate clips
        motions = ["zoom_in", "pan_right", "zoom_out", "pan_left"]
        clips = []
        for i, label in enumerate(ordered_labels):
            motion = motions[i % len(motions)]
            clip_path = self._generate_clip(label, groups[label], out_dir, per_clip, motion)
            clips.append(TourClip(label=label, image_paths=groups[label],
                                  clip_path=clip_path, duration_s=per_clip))

        # 4. Stitch
        final_path = os.path.join(out_dir, "photo_tour.mp4")
        clip_paths = [c.clip_path for c in clips]
        self._xfade(clip_paths, final_path, transition_dur)

        # 5. Thumbnail
        thumb_path = os.path.join(out_dir, "photo_tour_thumb.png")
        if os.path.exists(final_path):
            subprocess.run([
                self.ffmpeg, "-y", "-loglevel", "error",
                "-i", final_path, "-vframes", "1", "-s", "640x360", thumb_path
            ], capture_output=True, timeout=30)

        # 6. Verify final video
        size = os.path.getsize(final_path) if os.path.exists(final_path) else 0
        duration = self._probe_duration(final_path)

        return {
            "final_video": final_path,
            "thumbnail": thumb_path,
            "clips": [{"label": c.label, "path": c.clip_path, "images": len(c.image_paths)}
                      for c in clips],
            "scene_count": len(clips),
            "image_count": len(image_paths),
            "size_bytes": size,
            "duration_s": round(duration, 2),
            "resolution": f"{RES_W}x{RES_H}",
            "fps": FPS,
        }

    # ────────────────────────────────────────────────────────
    # VEO 3.1 PIPELINE (option A)
    # ────────────────────────────────────────────────────────
    def generate_veo(self, image_paths: list, out_dir: str, api_key: str,
                     target_duration: float = 45.0, transition_dur: float = 1.2,
                     model: str = None, classify: bool = True,
                     timeout_s: int = 600) -> dict:
        """Photos → Veo-generated cinematic tour.

        Classifies each photo into room scenes, generates one Veo 3.1 clip per
        scene (text-to-video from the room label, or image-to-video when a
        public image URL is supplied via `image_urls`), then stitches the clips
        with crossfade. Falls back to the local Ken Burns engine on any scene
        failure so a tour is still produced.
        """
        os.makedirs(out_dir, exist_ok=True)
        image_paths = [p for p in image_paths if os.path.exists(p)]
        if not image_paths:
            raise ValueError("No valid image paths provided")

        veo = VeoVideoGenerator(api_key, model=model)

        if classify:
            groups = self.build_groups(image_paths)
        else:
            groups = {"scene": image_paths}
        ordered_labels = self.order_labels(list(groups.keys()))

        clips = []
        veo_success = 0
        veo_fallback = 0
        for i, label in enumerate(ordered_labels):
            safe = re.sub(r"[^a-z0-9_]+", "_", label.lower()).strip("_") or f"scene_{i}"
            clip_path = os.path.join(out_dir, f"veo_{safe}.mp4")
            prompt = self._scene_prompt(label, groups[label])
            try:
                # Text-to-video: the prompt describes the room. (image_urls can
                # be passed here to enable image-to-video for public URLs.)
                veo.generate(prompt, clip_path, timeout_s=timeout_s)
                clips.append(TourClip(label=label, image_paths=groups[label],
                                      clip_path=clip_path, duration_s=0.0))
                veo_success += 1
            except Exception as e:
                # Graceful degradation: Ken Burns for this scene.
                fallback = os.path.join(out_dir, f"veo_{safe}_fb.mp4")
                motion = ["zoom_in", "pan_right", "zoom_out", "pan_left"][i % 4]
                self._generate_clip(label, groups[label], out_dir, 8.0, motion)
                # _generate_clip writes clip_<safe>.mp4 — reuse it
                fb = os.path.join(out_dir, f"clip_{safe}.mp4")
                if os.path.exists(fb):
                    shutil.copy2(fb, fallback)
                    clips.append(TourClip(label=label, image_paths=groups[label],
                                          clip_path=fallback, duration_s=8.0))
                    veo_fallback += 1
                print(f"⚠️  Veo failed for '{label}' — used Ken Burns fallback: {e}")

        if not clips:
            raise RuntimeError("No clips generated")

        final_path = os.path.join(out_dir, "photo_tour_veo.mp4")
        self._xfade([c.clip_path for c in clips], final_path, transition_dur)

        thumb_path = os.path.join(out_dir, "photo_tour_veo_thumb.png")
        if os.path.exists(final_path):
            subprocess.run([
                self.ffmpeg, "-y", "-loglevel", "error",
                "-i", final_path, "-vframes", "1", "-s", "640x360", thumb_path
            ], capture_output=True, timeout=30)

        size = os.path.getsize(final_path) if os.path.exists(final_path) else 0
        duration = self._probe_duration(final_path)

        # Honest engine attribution
        if veo_success > 0 and veo_fallback == 0:
            engine = "VEO_3.1"
        elif veo_success > 0 and veo_fallback > 0:
            engine = "VEO_3.1 + Ken Burns fallback (partial)"
        else:
            engine = "Ken Burns (Veo unavailable)"

        return {
            "final_video": final_path,
            "thumbnail": thumb_path,
            "clips": [{"label": c.label, "path": c.clip_path, "images": len(c.image_paths)}
                      for c in clips],
            "scene_count": len(clips),
            "image_count": len(image_paths),
            "size_bytes": size,
            "duration_s": round(duration, 2),
            "engine": engine,
            "model": veo.model,
            "veo_success": veo_success,
            "veo_fallback": veo_fallback,
        }

    @staticmethod
    def _scene_prompt(label: str, image_paths: list) -> str:
        """Build a cinematic Veo prompt from a room label."""
        name = label.replace("_", " ").strip()
        return (
            f"Cinematic slow pan through a {name}, photorealistic interior, "
            f"natural light, smooth camera motion, high detail, 16:9"
        )


# ═══════════════════════ CLI ═══════════════════════
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Vision 5D AI Photo Tour (local)")
    ap.add_argument("images", nargs="+", help="Input image paths")
    ap.add_argument("--out", default="output/photo_tour", help="Output directory")
    ap.add_argument("--duration", type=float, default=45.0)
    ap.add_argument("--transition", type=float, default=1.2)
    ap.add_argument("--no-classify", action="store_true")
    args = ap.parse_args()

    # Try to build a provider adapter for classification (optional)
    adapter = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from packages.ai.provider_client import ProviderAdapter, ProviderConfig
        cfg = ProviderConfig.from_env()
        if cfg.is_configured():
            adapter = ProviderAdapter(cfg)
    except Exception:
        adapter = None

    director = TourVisionDirector(adapter=adapter)
    result = director.generate(args.images, args.out,
                               target_duration=args.duration,
                               transition_dur=args.transition,
                               classify=not args.no_classify)
    print(json.dumps(result, indent=2))
