#!/usr/bin/env python3
import os
import sys
import subprocess
import re
from pathlib import Path

def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def find_video_parts(video_number, directory='.'):
    """Find all parts of a video with the given number."""
    pattern = f"{video_number}-*.mp4"
    files = sorted(Path(directory).glob(pattern))
    return [str(f) for f in files]

def find_subtitle_parts(video_number, directory='.'):
    """Find all subtitle parts with the given number."""
    pattern = f"{video_number}-*.srt"
    files = sorted(Path(directory).glob(pattern))
    return [str(f) for f in files]

def parse_srt_time(time_str):
    """Parse SRT timestamp to seconds."""
    # Format: HH:MM:SS,mmm
    match = re.match(r'(\d+):(\d+):(\d+),(\d+)', time_str)
    if match:
        h, m, s, ms = map(int, match.groups())
        return h * 3600 + m * 60 + s + ms / 1000
    return 0

def format_srt_time(seconds):
    """Format seconds to SRT timestamp."""
    ms = int((seconds % 1) * 1000)
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def offset_subtitle(subtitle_content, offset_seconds):
    """Offset all timestamps in a subtitle by given seconds."""
    lines = subtitle_content.strip().split('\n')
    result = []
    
    for line in lines:
        # Check if line contains timestamp
        if '-->' in line:
            parts = line.split(' --> ')
            if len(parts) == 2:
                start = parse_srt_time(parts[0])
                end = parse_srt_time(parts[1])
                new_start = format_srt_time(start + offset_seconds)
                new_end = format_srt_time(end + offset_seconds)
                result.append(f"{new_start} --> {new_end}")
            else:
                result.append(line)
        else:
            result.append(line)
    
    return '\n'.join(result)

def concatenate_videos(video_parts, output_path):
    """Concatenate videos using ffmpeg."""
    # Create a temporary file list for ffmpeg
    list_file = 'concat_list.txt'
    with open(list_file, 'w') as f:
        for video in video_parts:
            f.write(f"file '{video}'\n")
    
    # Run ffmpeg concat
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file,
        '-c', 'copy',
        output_path,
        '-y'  # Overwrite output file if exists
    ]
    
    subprocess.run(cmd, check=True)
    os.remove(list_file)
    print(f"✓ Created {output_path}")

def concatenate_subtitles(subtitle_parts, video_parts, output_path):
    """Concatenate subtitles with proper time offsets."""
    combined_srt = []
    subtitle_counter = 1
    current_offset = 0
    
    for i, (srt_file, video_file) in enumerate(zip(subtitle_parts, video_parts)):
        # Read subtitle content
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Offset the subtitle
        if i > 0:
            content = offset_subtitle(content, current_offset)
        
        # Renumber subtitles
        lines = content.strip().split('\n\n')
        for block in lines:
            block_lines = block.split('\n')
            if block_lines:
                # Replace the subtitle number
                block_lines[0] = str(subtitle_counter)
                combined_srt.append('\n'.join(block_lines))
                subtitle_counter += 1
        
        # Update offset for next subtitle
        if i < len(video_parts) - 1:
            duration = get_video_duration(video_file)
            current_offset += duration
    
    # Write combined subtitle
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(combined_srt) + '\n')
    
    print(f"✓ Created {output_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <video_number>")
        print("Example: python script.py 0005")
        sys.exit(1)
    
    video_number = sys.argv[1]
    directory = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    # Find video and subtitle parts
    video_parts = find_video_parts(video_number, directory)
    subtitle_parts = find_subtitle_parts(video_number, directory)
    
    if not video_parts:
        print(f"Error: No video parts found for {video_number}")
        sys.exit(1)
    
    print(f"Found {len(video_parts)} video part(s):")
    for v in video_parts:
        print(f"  - {v}")
    
    # Create output paths in the same directory as the video parts
    output_video = os.path.join(directory, f"{video_number}.mp4")
    print(f"\nConcatenating videos to {output_video}...")
    concatenate_videos(video_parts, output_video)
    
    # Concatenate subtitles if available
    if subtitle_parts:
        print(f"\nFound {len(subtitle_parts)} subtitle part(s):")
        for s in subtitle_parts:
            print(f"  - {s}")
        
        output_subtitle = os.path.join(directory, f"{video_number}.srt")
        print(f"\nConcatenating subtitles to {output_subtitle}...")
        concatenate_subtitles(subtitle_parts, video_parts, output_subtitle)
    else:
        print("\nNo subtitle files found, skipping subtitle concatenation.")
    
    print("\n✓ Done!")

if __name__ == '__main__':
    main()