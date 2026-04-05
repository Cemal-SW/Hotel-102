import os
import glob

template_dir = r"c:\Users\Msı\Desktop\Hotel-102\Hotel-102\templates"
html_files = glob.glob(os.path.join(template_dir, "*.html"))

old_btn = '<button class="bg-primary text-on-primary px-8 py-3 rounded-full font-label text-sm tracking-widest hover:bg-on-primary-container transition-all duration-400 shadow-sm">Book Now</button>'
new_btn = '<a href="{{ url_for(\'booking\') }}" class="bg-primary text-on-primary px-8 py-3 rounded-full font-label text-sm tracking-widest hover:bg-on-primary-container transition-all duration-400 shadow-sm">Book Now</a>'

for file in html_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    if old_btn in content:
        content = content.replace(old_btn, new_btn)
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file}")
