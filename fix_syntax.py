import os
import glob

template_dir = r"c:\Users\Msı\Desktop\Hotel-102\Hotel-102\templates"
html_files = glob.glob(os.path.join(template_dir, "*.html"))

for file in html_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content.replace("url_for(\\'booking\\')", "url_for('booking')")
    
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {file}")
