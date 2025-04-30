"""
Video Quality Comparison Tool
-----------------------------
Compares two videos using VMAF metrics via ffmpeg-quality-metrics.
Also supports downloading videos from YouTube for comparison.
"""

import argparse
import json
import subprocess
import sys
import os
import tempfile

def download_youtube_video(url, output_path=None):
    """Download YouTube video at the highest quality using yt-dlp."""
    if output_path is None:
        # Create a temporary file with .mp4 extension
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "youtube_download.mp4")
    
    print(f"Downloading YouTube video from: {url}")
    print(f"Saving to: {output_path}")
    
    try:
        cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", url, "-o", output_path]
        subprocess.run(cmd, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error downloading YouTube video: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: yt-dlp not found. Install it with: pip install yt-dlp")
        sys.exit(1)

def run_video_comparison(reference_video, distorted_video, metrics=None):
    """Run video quality comparison using ffmpeg-quality-metrics."""
    if metrics is None:
        metrics = ["vmaf"]
    
    metrics_str = " ".join(metrics)
    cmd = ["ffmpeg-quality-metrics", reference_video, distorted_video, "--metrics", *metrics]
    
    print(f"Running comparison between:")
    print(f"Reference:  {reference_video}")
    print(f"Distorted:  {distorted_video}")
    print(f"Using metrics: {metrics_str}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running ffmpeg-quality-metrics: {e}")
        print(f"Command output: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error parsing output. Raw output: {result.stdout}")
        sys.exit(1)

def display_results(results):
    """Format and display the quality assessment results."""
    print("\n=== VIDEO QUALITY ASSESSMENT RESULTS ===\n")
    
    for metric, data in results.items():
        print(f"=== {metric.upper()} Results ===")
        
        if metric == "vmaf":
            # Handle VMAF specific output
            vmaf_score = data.get('mean', None)
            if vmaf_score:
                print(f"VMAF Score: {vmaf_score:.2f} / 100.0")
                
                # Interpretation guidelines for VMAF
                print("\n=== VMAF SCORE INTERPRETATION ===")
                print("0-20:   Bad quality")
                print("20-40:  Poor quality")
                print("40-60:  Fair quality")
                print("60-80:  Good quality")
                print("80-100: Excellent quality")
                
                quality_tier = "Bad" if vmaf_score < 20 else \
                               "Poor" if vmaf_score < 40 else \
                               "Fair" if vmaf_score < 60 else \
                               "Good" if vmaf_score < 80 else "Excellent"
                print(f"\nThis video's quality is rated as: {quality_tier}")
            
            # Print frame-by-frame details if available
            if 'frames' in data and data['frames']:
                print("\n=== Frame-by-Frame Details ===")
                print(f"Analyzed {len(data['frames'])} frames")
                print(f"Min VMAF: {min(frame.get('metrics', {}).get('vmaf', 0) for frame in data['frames']):.2f}")
                print(f"Max VMAF: {max(frame.get('metrics', {}).get('vmaf', 0) for frame in data['frames']):.2f}")
        
        elif metric in ["psnr", "ssim"]:
            # Handle other metrics
            for component, value in data.items():
                if component != 'frames':
                    print(f"{metric.upper()} {component}: {value:.4f}")
        
        else:
            # Generic handling for other potential metrics
            print(json.dumps(data, indent=2))
        
        print("")  # Empty line between metrics

def main():
    parser = argparse.ArgumentParser(description="Compare video quality using ffmpeg-quality-metrics")
    
    # Create a mutually exclusive group for the first video source
    video1_group = parser.add_mutually_exclusive_group(required=True)
    video1_group.add_argument("--reference", help="Path to the reference (original) video")
    video1_group.add_argument("--youtube", help="YouTube URL to download as reference video")
    
    # Second video is always a file path
    parser.add_argument("--distorted", required=True, help="Path to the distorted (compressed) video")
    
    # Optional arguments
    parser.add_argument("--youtube-output", help="Output path for the downloaded YouTube video")
    parser.add_argument("--metrics", nargs='+', default=["vmaf"], 
                        choices=["vmaf", "psnr", "ssim"], 
                        help="Metrics to use for comparison (default: vmaf)")
    
    args = parser.parse_args()
    
    # Handle YouTube download if specified
    reference_video = None
    if args.youtube:
        reference_video = download_youtube_video(args.youtube, args.youtube_output)
    else:
        reference_video = args.reference
    
    # Check if files exist
    for video_path in [reference_video, args.distorted]:
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            sys.exit(1)
    
    # Run comparison
    results = run_video_comparison(reference_video, args.distorted, args.metrics)
    
    # Display results
    display_results(results)

if __name__ == "__main__":
    main()