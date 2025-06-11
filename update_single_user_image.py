import requests
from bs4 import BeautifulSoup
import re
import os
import yaml
import subprocess
import sys


def get_latest_version(package_name):
    """
    Function to get the latest version of a conda package from Conda-Forge

    """
    url = f"https://anaconda.org/conda-forge/{package_name}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error: Could not fetch data for {package_name}. Status code {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    version_tag = soup.find('small', {'class': 'subheader', 'style': 'font-size: 20px'})
    
    if version_tag:
        return version_tag.text.strip()
    return None


def get_pip_package_version(package_name):
    """
    Function to get the latest version of a pip package from PyPI

    """
    # Remove any extras (e.g., '[webpdf]') from the package name
    base_package_name = re.sub(r'\[.*\]', '', package_name)
    
    url = f"https://pypi.org/pypi/{base_package_name}/"
    
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error: Could not fetch data for {base_package_name}. Status code {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the version in the <h1> tag with class 'package-header__name'
    version_tag = soup.find('h1', {'class': 'package-header__name'})
    
    if version_tag:
        # Extract the version from the text in the <h1> tag
        version_text = version_tag.text.strip()
        
        # Extract the version number from the text (e.g., "nbconvert 7.16.6")
        match = re.search(r'(\d+\.\d+\.\d+)', version_text)
        if match:
            return match.group(1)
    
    print(f"Error: Could not find the version for {base_package_name}.")
    return None


def is_valid_version(version):
    """
    Function to check if a version is in the correct format

    """
    return bool(re.match(r'^\d+\.\d+\.\d+$', version))  # matches x.x.x format


def parse_yaml_with_comments(file_path):
    """
    Function to parse the environment.yml file and capture all sections and comments

    """
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    content = []
    dependencies = []
    pip_dependencies = []
    comments = []  # to store all comments
    current_section = None
    
    for line in lines:
        stripped_line = line.strip()
        
        # If the line is a comment, capture it
        if stripped_line.startswith('#'):
            comments.append(line)
            content.append(line)
        
        # If the line is a section header (e.g., 'dependencies:')
        elif stripped_line.endswith(':'):
            current_section = stripped_line[:-1]
            content.append(line)
        
        # If we are in the dependencies section, capture the dependencies
        elif current_section == 'dependencies' and '==' in stripped_line:
            # Capture the entire line including the '-' before the package name
            dependencies.append(line.strip())
            content.append(line)
        
        # For pip dependencies section
        elif current_section == '- pip' and '==' in stripped_line:
            pip_dependencies.append(line.strip())
            content.append(line)
        
        # For other sections like 'name', 'channels', 'pip', we just capture the lines
        else:
            content.append(line)
    
    return content, dependencies, pip_dependencies


def update_environment_yaml(input_file_path, output_file_path):
    """
    Function to create the new environment.yml with updated versions

    """

    content, dependencies, pip_dependencies = parse_yaml_with_comments(input_file_path)
    
    # Store the latest versions in a dictionary for conda packages
    version_dict = {}
    for dep in dependencies:
        match = re.match(r'(\s*)(-?\s*)(\S+)(\[[^\]]+\])?==(.+)', dep)  # Capture leading spaces, '-' before package name, package name, and version
        
        if match:
            leading_spaces = match.group(1)
            dash = match.group(2)
            package_name = match.group(3)
            current_version = match.group(5)
            
            # Get the latest version for conda packages
            print(f"Checking for latest version of {package_name}...")
            latest_version = get_latest_version(package_name)
            
            if latest_version and is_valid_version(latest_version):
                print(f"Found latest version for {package_name}: {latest_version}")
                version_dict[package_name] = latest_version
            else:
                print(f"Could not fetch a valid version for {package_name}, keeping the current version.")
                version_dict[package_name] = current_version
    
    # Update pip packages and dependencies
    pip_version_dict = {}
    for dep in pip_dependencies:
        match = re.match(r'(\s*)(-?\s*)(\S+)(\[[^\]]+\])?==(.+)', dep)  
        
        if match:
            leading_spaces = match.group(1)
            dash = match.group(2)
            package_name = match.group(3)
            current_version = match.group(5)
            
            # Get the latest version for pip packages
            print(f"Checking for latest pip version of {package_name}...")
            latest_version = get_pip_package_version(package_name)
            
            if latest_version and is_valid_version(latest_version):
                print(f"Found latest pip version for {package_name}: {latest_version}")
                pip_version_dict[package_name] = latest_version
            else:
                print(f"Could not fetch a valid pip version for {package_name}, keeping the current version.")
                pip_version_dict[package_name] = current_version

    # Update the dependencies and pip dependencies sections
    updated_content = []
    
    for line in content:
        stripped_line = line.strip()
        print(stripped_line)

        match = re.match(r'(\s*)(-?\s*)(\S+)(\[[^\]]+\])?==(.+)', line)  
        if match:
            leading_spaces = match.group(1)
            dash = match.group(2)
            package_name = match.group(3)
            current_version = match.group(4)
            
            if package_name in version_dict:
                updated_content.append(f"{leading_spaces}{dash}{package_name}=={version_dict[package_name]}\n")
            elif package_name in pip_version_dict:
                updated_content.append(f"{leading_spaces}{dash}{package_name}=={pip_version_dict[package_name]}\n")
            else:
                updated_content.append(line)
        # Keep all other lines (including comments, channels, etc.) unchanged
        else:
            updated_content.append(line)
    
    # Write the updated content to the new file
    with open(output_file_path, 'w') as file:
        file.writelines(updated_content)
    
    print(f"Updated environment.yml saved as {output_file_path}.")


def main():
    yaml_file_path = 'environment.yml'
    output_file_path = 'updated_environment.yml'
    
    if not os.path.exists(yaml_file_path):
        print(f"Error: The file {yaml_file_path} does not exist.")
        return
    
    update_environment_yaml(yaml_file_path, output_file_path)

if __name__ == '__main__':
    main()
