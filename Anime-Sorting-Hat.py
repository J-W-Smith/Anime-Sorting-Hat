import os
import shutil
import re

# Get the current working directory
directory = os.getcwd()

# Regular expression pattern to extract season number like 'S01E09'
pattern = re.compile(r'S(\d{2})E\d{2}')

# Loop through each file in the directory
for filename in os.listdir(directory):
    if filename.endswith('.mkv'):
        # Extract the anime name and season number using regex pattern
        match = pattern.search(filename)
        
        if match:
            season_number = match.group(1)  # Extract the two-digit season number
            anime_name = filename.split('] ')[1].split(' - ')[0]
            
            # Create the season directory if it doesn't exist
            season_dir = os.path.join(directory, anime_name, f"Season {season_number}")
            if not os.path.exists(season_dir):
                os.makedirs(season_dir)
            
            # Set the destination path inside the season directory
            destination_path = os.path.join(season_dir, filename)
        else:
            # If no season pattern is found, place the file in the anime directory
            anime_name = filename.split('] ')[1].split(' - ')[0]
            destination_path = os.path.join(directory, anime_name, filename)
            
            # Create the anime directory if it doesn't exist
            anime_dir = os.path.join(directory, anime_name)
            if not os.path.exists(anime_dir):
                os.makedirs(anime_dir)
        
        # Construct the source path for the .mkv file
        source_path = os.path.join(directory, filename)
        
        # Check if source file exists before attempting to move it
        if os.path.exists(source_path):
            # Move the .mkv file to the respective destination path
            shutil.move(source_path, destination_path)
        else:
            print(f"Source file {source_path} not found!")
