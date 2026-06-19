import sys
import streamlit as st
from downloader import download_video
from transcriber import transcribe_audio
from analyzer import find_clip_moments
from cutter import slice_video

def run_pipeline(url: str) -> dict:
    "Run the full pipeline: download, transcribe, analyze, and slice"

    result = {"error": None}

    # Download
    st.write("Downloading video...")
    download_result = download_video(url)
    if download_result.get("error"):
        result["error"] = f"Download failed: {download_result['error']}"
        return result

    result["download"] = download_result

    # Transcribe
    st.write("Transcribing audio...")
    transcribe_result = transcribe_audio(download_result["filepath"])
    if transcribe_result.get("error"):
        result["error"] = f"Transcription failed: {transcribe_result['error']}"
        return result

    result["transcription"] = transcribe_result

    # Analyze
    st.write("Finding clip moments...")
    clip_moments = find_clip_moments(transcribe_result)
    if not clip_moments:
        result["error"] = "No clip moments found"
        return result

    # Handle potential variations in JSON keys
    clips_key = next((key for key in clip_moments[0] if "clip" in key.lower()), None)
    if clips_key:
        result["clips"] = clip_moments[0][clips_key]
    else:
        result["clips"] = clip_moments

    # Slice
    st.write("Slicing video...")
    output_paths = slice_video(download_result["filepath"], result["clips"])
    if not output_paths:
        result["error"] = "Failed to slice video"
        return result

    result["output_paths"] = output_paths
    return result

def main():
    "Streamlit UI for the full pipeline"

    st.title("Video Clip Generator")

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = st.text_input("Enter video URL")

    if url:
        with st.spinner("Processing..."):
            result = run_pipeline(url)

            if result.get("error"):
                st.error(f"Error: {result['error']}")
            else:
                st.success("Processing complete!")
                st.write(f"Title: {result['download']['title']}")
                st.write(f"Duration: {result['download']['duration_seconds']} seconds")

                st.write("Clip moments:")
                for i, clip in enumerate(result["clips"]):
                    st.write(f"Clip {i+1}:")
                    st.write(f"Start: {clip['start']}s")
                    st.write(f"End: {clip['end']}s")
                    if "hook_text" in clip:
                        st.write(f"Hook: {clip['hook_text']}")
                    if "retention_strategy" in clip:
                        st.write(f"Strategy: {clip['retention_strategy']}")

                st.write("Output files:")
                for path in result["output_paths"]:
                    st.write(f"- {path}")

if __name__ == "__main__":
    main()
