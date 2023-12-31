import os
import shutil
import re

# Get the current working directory
directory = os.getcwd()

# Regular expression pattern to extract season number like 'S3', 'S4', etc.
pattern = re.compile(r'S(\d+)')

# Loop through each file in the directory
for filename in os.listdir(directory):
    if filename.endswith('.mkv'):
        # Extract the anime name and season number using regex pattern
        match = pattern.search(filename)
        
        if match:
            season_number = match.group(1)  # Extract the season number (like '3' from 'S3')
            
            # Extract anime name by looking for the space-dash-space pattern
            anime_and_subgroup = filename.split(' - ')[0].split('] ')[1]  # Extract anime name and subgroup
            
            # Splitting based on the space-dash-space pattern and then looking for the S[number] just before that
            anime_name = anime_and_subgroup.rsplit(' S' + season_number, 1)[0].strip()
            
            print(f"Detected anime name: {anime_name}, Season: {season_number}")  # Debugging line
            
            # Create the anime directory if it doesn't exist
            anime_dir = os.path.join(directory, anime_name)
            if not os.path.exists(anime_dir):
                os.makedirs(anime_dir)
            
            # Create the season directory if it doesn't exist
            season_dir = os.path.join(anime_dir, f"Season {season_number}")
            if not os.path.exists(season_dir):
                os.makedirs(season_dir)
            
            # Set the destination path inside the season directory
            destination_path = os.path.join(season_dir, filename)
            
        else:
            # If no season pattern is found, place the file directly in the anime directory
            anime_and_subgroup = filename.split(' - ')[0].split('] ')[1]  # Extract anime name and subgroup
            anime_name = anime_and_subgroup.split(' S')[0].strip()  # Extract anime name without brackets
            
            print(f"Detected anime name (No Season): {anime_name}")  # Debugging line
            
            # Create the anime directory if it doesn't exist
            anime_dir = os.path.join(directory, anime_name)
            if not os.path.exists(anime_dir):
                os.makedirs(anime_dir)
            
            # Set the destination path in the anime directory
            destination_path = os.path.join(anime_dir, filename)
        
        # Construct the source path for the .mkv file
        source_path = os.path.join(directory, filename)
        
        # Check if source file exists before attempting to move it
        if os.path.exists(source_path):
            # Move the .mkv file to the respective destination path
            shutil.move(source_path, destination_path)
        else:
            print(f"Source file {source_path} not found!")
