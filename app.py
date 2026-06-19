import streamlit as st
from downloader import download_video

def main():
    "Minimal Streamlit UI for video downloading"

    st.title("Video Downloader")

    url = st.text_input("Enter video URL")

    if st.button("Download"):
        with st.spinner("Downloading..."):
            result = download_video(url)

            if result.get("error"):
                st.error(f"Error: {result['error']}")
            else:
                st.success("Download complete!")
                st.write(f"Title: {result['title']}")
                st.write(f"Duration: {result['duration_seconds']} seconds")

if __name__ == "__main__":
    main()
