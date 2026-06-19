import os
import subprocess

def slice_video(video_path: str, clips: list) -> list:
    "Slice video into clips using ffmpeg"

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    output_paths = []

    for i, clip in enumerate(clips):
        start = clip["start"]
        duration = clip["end"] - clip["start"]
        output_path = os.path.join(output_dir, f"clip_{i+1}.mp4")

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", str(start),
            "-t", str(duration),
            "-c", "copy",
            output_path,
            "-y"
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            output_paths.append(output_path)
        except subprocess.CalledProcessError as e:
            print(f"Error slicing clip {i+1}: {e.stderr.decode()}")

    return output_paths

if __name__ == "__main__":
    # Test block
    downloads_dir = "downloads"
    test_file = None

    if os.path.exists(downloads_dir):
        for filename in os.listdir(downloads_dir):
            if filename.endswith((".webm", ".mp4")):
                test_file = os.path.join(downloads_dir, filename)
                break

    if not test_file:
        print("Error: No .webm or .mp4 files found in the downloads directory")
    else:
        # Mock clip moments
        mock_clips = [
            {"start": 10, "end": 25},
            {"start": 40, "end": 55}
        ]

        output_paths = slice_video(test_file, mock_clips)

        if output_paths:
            print("Successfully created clips:")
            for path in output_paths:
                print(f"- {path}")
        else:
            print("Failed to create clips")
