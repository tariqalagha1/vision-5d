#!/usr/bin/env bash
# Encode motion frames -> 1280x720 24fps MP4 (H.264 yuv420p for max compatibility)
set -e
cd "C:/Users/admin/workspaces/vision-5d"
FRAMES="evidence/V5D-REALITY-CHECK/motion_frames"
OUT="evidence/V5D-REALITY-CHECK/motion_clip.mp4"
ffmpeg -y -v error -framerate 24 -i "$FRAMES/frame_%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 18 -r 24 "$OUT"
echo "ENCODED: $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,r_frame_rate,codec_name -of default=noprint_wrappers=1 "$OUT"
