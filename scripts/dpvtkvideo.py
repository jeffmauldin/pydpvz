import argparse
import sys
import subprocess
import shutil
import glob
import os

def create_video(input_file, output_mp4, view_direction=None, timesteprange=None, keep_frames=False):
    # Base name for temporary frames
    base_name = "tmp_video_frames"
    
    # 1. Build the command to run dpvtkanimate.py
    cmd = [
        "bash", "-c",
        f"source scripts/setup_env.sh && ./paraview_v610/bin/pvbatch --sym --mesa scripts/dpvtkanimate.py {input_file} {base_name}"
    ]
    
    if view_direction:
        cmd[2] += f" --viewdirection \"{view_direction}\""
    if timesteprange:
        cmd[2] += f" --timesteprange \"{timesteprange}\""
        
    print(f"Executing: {cmd[2]}")
    
    # Run pvbatch
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Error: dpvtkanimate.py failed to generate frames.")
        sys.exit(1)
        
    print("Frames generated successfully.")
    
    # 2. Check for ffmpeg
    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found in PATH, skipping video encoding.")
        if not keep_frames:
            print("Note: frames will remain on disk because they were not encoded.")
        return
        
    print(f"Encoding video to {output_mp4} using ffmpeg...")
    
    # ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-framerate", "10",
        "-i", f"{base_name}_%04d.png",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        output_mp4
    ]
    
    ff_result = subprocess.run(ffmpeg_cmd)
    
    if ff_result.returncode != 0:
        print("Error: ffmpeg failed to encode video.")
        sys.exit(1)
        
    print(f"Successfully created {output_mp4}")
    
    # 3. Clean up frames
    if not keep_frames:
        print("Cleaning up temporary frames...")
        frames = glob.glob(f"{base_name}_*.png")
        for f in frames:
            os.remove(f)
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an MP4 video from a .dpvtk file.")
    parser.add_argument("input", help="Input .dpvtk file")
    parser.add_argument("output", help="Output .mp4 file")
    parser.add_argument("--viewdirection", "-vwdr", default="[0.0, 0.0, -1.0]",
                        help="Optional look direction vector, e.g. '[0, 0, -1]'.")
    parser.add_argument("--timesteprange", default=None,
                        help="Optional range of timesteps to render, e.g. '[24,36]'.")
    parser.add_argument("--keep-frames", action="store_true", help="Keep generated PNG frames after encoding")

    args = parser.parse_args()
    create_video(args.input, args.output, args.viewdirection, args.timesteprange, args.keep_frames)
