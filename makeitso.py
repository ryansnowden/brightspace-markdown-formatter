import re
from bs4 import BeautifulSoup
import os
import glob
import html2text
import shutil
from bs4 import NavigableString

def clean_html(html_content):
    # Create BeautifulSoup object
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Handle YouTube embeds - convert to plain links
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '')
        if 'youtube' in src.lower():
            # Extract video ID and create plain link
            video_id = re.search(r'(?:embed/|v=|v/|watch\?v=)([a-zA-Z0-9_-]+)', src)
            if video_id:
                video_id = video_id.group(1)
                link = f'https://www.youtube.com/watch?v={video_id}'
                # Create text node directly instead of using angle brackets
                new_tag = soup.new_string(link)
                iframe.replace_with(new_tag)
                # Remove extra newline if it exists
                if iframe.next_sibling and isinstance(iframe.next_sibling, NavigableString):
                    iframe.next_sibling.replace_with('')
    
    # Remove the head section
    if soup.head:
        soup.head.decompose()
    
    # Remove script tags and their contents
    for script in soup.find_all('script'):
        script.decompose()
    
    # Remove style tags and their contents
    for style in soup.find_all('style'):
        style.decompose()
    
    # Remove div with class 'banner-img'
    for banner in soup.find_all('div', class_='banner-img'):
        banner.decompose()
    
    # Remove div with class 'card-graphic' and its contents
    for card in soup.find_all('div', class_='card-graphic'):
        card.decompose()
    
    # Remove empty tags
    for tag in soup.find_all():
        if len(tag.get_text(strip=True)) == 0 and len(tag.find_all()) == 0:
            tag.decompose()
    
    # Remove all id attributes
    for tag in soup.find_all(attrs={'id': True}):
        del tag['id']
    
    # Get the cleaned HTML
    cleaned_html = str(soup)
    
    # Remove any remaining JavaScript event handlers
    cleaned_html = re.sub(r' on\w+="[^"]*"', '', cleaned_html)
    cleaned_html = re.sub(r" on\w+='[^']*'", '', cleaned_html)
    
    return cleaned_html

def convert_to_markdown(html_content):
    # Initialize html2text
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.body_width = 0
    
    # Convert to markdown
    markdown_content = converter.handle(html_content)
    return markdown_content

def get_main_number(filename):
    # Extract the first number from the filename
    match = re.match(r'^(\d+)', filename)
    if match:
        return match.group(1)
    return None

def create_folder_if_not_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def clean_markdown(content):
    """
    Clean markdown content by removing extra blank lines at the beginning and end,
    and removing BOM characters.
    Args:
        content: The markdown content to clean
    Returns:
        Cleaned markdown content
    """
    # Remove BOM if present
    if content.startswith('\ufeff'):
        content = content[1:]
    
    # Split into lines, strip empty lines from start and end
    lines = content.splitlines()
    
    # Find first non-empty line
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    
    # Find last non-empty line
    end = len(lines) - 1
    while end >= 0 and not lines[end].strip():
        end -= 1
    
    # Get the content between first and last non-empty lines
    if start <= end:
        cleaned_lines = lines[start:end + 1]
        
        # Remove blank lines after YouTube links
        result_lines = []
        for i, line in enumerate(cleaned_lines):
            result_lines.append(line)
            if 'youtube.com/watch?v=' in line and i < len(cleaned_lines) - 1:
                if not cleaned_lines[i + 1].strip():
                    continue
            
        return '\n'.join(result_lines)
    return content

def clean_html_file(input_file, output_file):
    try:
        # Read the input HTML file
        with open(input_file, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Prettify the HTML
        prettified_html = soup.prettify()
        
        # Extract image references from prettified HTML
        soup = BeautifulSoup(prettified_html, 'html.parser')
        image_refs = [img.get('src') for img in soup.find_all('img') if img.get('src')]
        
        # Find text alternative links
        text_alt_links = []
        for link in soup.find_all('a'):
            link_text = link.get_text().lower()
            href = link.get('href')
            if href and ('text alternative' in link_text or 'text version' in link_text):
                text_alt_links.append(href)
        
        # Clean the prettified HTML
        cleaned_html = clean_html(prettified_html)
        
        # Convert to markdown
        markdown_content = convert_to_markdown(cleaned_html)
        
        # Clean the markdown content
        markdown_content = clean_markdown(markdown_content)
        
        # Get the main number and create folder
        main_number = get_main_number(os.path.basename(input_file))
        
        # Use the original filename for output
        output_file = os.path.splitext(input_file)[0] + '.md'
        original_output = output_file
        
        if main_number:
            folder_path = os.path.join(os.path.dirname(input_file), main_number)
            create_folder_if_not_exists(folder_path)
            output_file = os.path.join(folder_path, os.path.basename(output_file))
        
        # Write the markdown to output file
        with open(original_output, 'w', encoding='utf-8') as file:
            file.write(markdown_content)
            
        # Move markdown file to the numbered folder
        if main_number and original_output != output_file:
            os.rename(original_output, output_file)
            print(f"Successfully converted {input_file} to markdown and moved to {output_file}")
        else:
            print(f"Successfully converted {input_file} to markdown and saved to {original_output}")
        
        # Process text alternative files
        input_dir = os.path.dirname(input_file)
        target_dir = os.path.dirname(output_file)
        
        for alt_link in text_alt_links:
            alt_filename = os.path.basename(alt_link)
            alt_file_path = os.path.join(input_dir, alt_filename)
            
            if os.path.exists(alt_file_path):
                # Read and convert text alternative file
                with open(alt_file_path, 'r', encoding='utf-8') as file:
                    alt_content = file.read()
                
                alt_soup = BeautifulSoup(alt_content, 'html.parser')
                cleaned_alt = clean_html(str(alt_soup))
                alt_markdown = convert_to_markdown(cleaned_alt)
                
                # Create markdown filename for alternative text
                alt_md_filename = os.path.splitext(alt_filename)[0] + '_text_alternative.md'
                alt_md_path = os.path.join(target_dir, alt_md_filename)
                
                # Write alternative text markdown
                with open(alt_md_path, 'w', encoding='utf-8') as file:
                    file.write(alt_markdown)
                print(f"Created text alternative markdown: {alt_md_path}")
        
        # Move referenced images to the same directory as markdown
        for img_path in image_refs:
            # Get just the filename from the path
            img_filename = os.path.basename(img_path)
            # Construct source and destination paths
            src_path = os.path.join(input_dir, img_filename)
            dst_path = os.path.join(target_dir, img_filename)
            # Move the image if it exists and isn't already in the right place
            if os.path.exists(src_path) and src_path != dst_path:
                shutil.copy2(src_path, dst_path)
                print(f"Copied image to: {dst_path}")
        
        # Remove any cleaned*.html files in the same directory
        cleaned_files = glob.glob(os.path.join(input_dir, "cleaned*.html"))
        for cleaned_file in cleaned_files:
            os.remove(cleaned_file)
            print(f"Removed cleaned HTML file: {cleaned_file}")
        
        # Remove the original HTML file
        # os.remove(input_file)
        print(f"Removed original HTML file: {input_file}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def process_all_html_files():
    # Get all HTML files in the current directory
    html_files = glob.glob("*.html")
    
    if not html_files:
        print("No HTML files found in the current directory")
        return
    
    # Sort files to process them in order
    html_files.sort()
    
    for html_file in html_files:
        output_file = html_file
        try:
            clean_html_file(html_file, output_file)
            print(f"Processed {html_file} -> {output_file}")
        except Exception as e:
            print(f"Error processing {html_file}: {str(e)}")

def combine_markdown_files():
    """
    For each numbered folder, combines all markdown files within that folder into a single file,
    placing the combined file inside the respective folder. Files are sorted by name before combining.
    Skips processing the combined output file itself. The output filename includes the folder name.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get all numbered folders
    numbered_folders = []
    for item in os.listdir(base_dir):
        if os.path.isdir(os.path.join(base_dir, item)) and item.isdigit():
            numbered_folders.append(item)
    
    # Sort folders numerically
    numbered_folders.sort(key=int)
    
    # Process each numbered folder independently
    for folder in numbered_folders:
        folder_path = os.path.join(base_dir, folder)
        output_filename = f'week_{folder}.md'
        output_file = os.path.join(folder_path, output_filename)
        
        # Find introduction file for this week
        intro_file = os.path.join(base_dir, f'Introduction to Week {folder}.md')
        
        # Find all markdown files in the folder
        markdown_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                # Skip any combined markdown files
                if file.endswith('.md') and not file.startswith('week_'):
                    full_path = os.path.join(root, file)
                    markdown_files.append(full_path)
        
        # Skip if no markdown files found
        if not markdown_files:
            print(f"No markdown files found in folder {folder}")
            continue
        
        # Sort files by name
        markdown_files.sort()
        
        # Create the combined file for this folder
        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.write(f'# Week {folder}\n\n')
            
            # Add introduction content if it exists
            if os.path.exists(intro_file):
                with open(intro_file, 'r', encoding='utf-8') as infile:
                    intro_content = infile.read()
                    cleaned_intro = clean_markdown(intro_content)
                    outfile.write(cleaned_intro)
            
            # Process each markdown file
            for md_file in markdown_files:
                with open(md_file, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    # Clean the content
                    cleaned_content = clean_markdown(content)
                    # Add file name as subheader (without extension)
                    file_name = os.path.splitext(os.path.basename(md_file))[0]
                    outfile.write(f'## {file_name}\n\n')
                    outfile.write(cleaned_content)
                    outfile.write('\n\n---\n\n')  # Add separator between files
        
        print(f"Created {output_filename} in folder {folder}")

def combine_markdown_files_custom():
    """
    Combines markdown files from numbered directories and base directory into a single 'combined.md'
    with custom processing to ensure clean and consistent output.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(base_dir, 'combined.md')
    
    # Collect markdown files
    markdown_files = []
    
    # Find only week summary files in numbered directories
    for item in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, item)
        if os.path.isdir(folder_path) and item.isdigit():
            week_file = os.path.join(folder_path, f'week_{item}.md')
            if os.path.exists(week_file):
                markdown_files.append(week_file)
    
    # Find markdown files in base directory
    base_dir_markdown_files = [f for f in os.listdir(base_dir) if f.endswith('.md') and 'Summary' in f]
    markdown_files.extend([os.path.join(base_dir, f) for f in base_dir_markdown_files])
    
    # Sort files by the folder number
    markdown_files.sort(key=lambda x: int(re.findall(r'\d+', os.path.basename(x))[0]) if re.findall(r'\d+', os.path.basename(x)) else float('inf'))
    
    # Combine files
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for file_path in markdown_files:
            with open(file_path, 'r', encoding='utf-8') as infile:
                content = infile.read()
                content = content.strip()
                outfile.write(content + '\n\n---\n\n')
    
    print(f"Combined {len(markdown_files)} markdown files into {output_file}")

if __name__ == "__main__":
    process_all_html_files()
    combine_markdown_files()
    combine_markdown_files_custom()
