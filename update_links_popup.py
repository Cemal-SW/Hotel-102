import os
import glob

template_dir = r"c:\Users\Msı\Desktop\Hotel-102\Hotel-102\templates"
html_files = glob.glob(os.path.join(template_dir, "*.html"))

for file in html_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Avoid replacing if it's already a popup
    if 'window.open(' not in content:
        old_url = 'href="{{ url_for(\'booking\') }}" class="bg-primary'
        new_url = 'href="#" onclick="window.open(\'{{ url_for(\\\'booking\\\') }}\', \'BookingEngine\', \'width=1100,height=850,scrollbars=yes\'); return false;" class="bg-primary'
        
        if old_url in content:
            content = content.replace(old_url, new_url)
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {file}")
