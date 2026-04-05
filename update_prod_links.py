import os
import glob
import re

template_dir = r"c:\Users\Msı\Desktop\Hotel-102\Hotel-102\templates"
html_files = glob.glob(os.path.join(template_dir, "*.html"))

for file in html_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # We want to replace the crazy popup string:
    # href="#" onclick="window.open('{{ url_for('booking') }}', 'BookingEngine', 'width=1100,height=850,scrollbars=yes'); return false;"
    old_tgt_1 = 'href="#" onclick="window.open(\'{{ url_for(\\\'booking\\\') }}\', \'BookingEngine\', \'width=1100,height=850,scrollbars=yes\'); return false;"'
    old_tgt_2 = 'href="#" onclick="window.open(\'{{ url_for(\'booking\') }}\', \'BookingEngine\', \'width=1100,height=850,scrollbars=yes\'); return false;"'
    
    new_tgt = 'href="{{ BOOKING_URL }}" target="_blank"'

    modified = False
    if old_tgt_1 in content:
        content = content.replace(old_tgt_1, new_tgt)
        modified = True
    if old_tgt_2 in content:
        content = content.replace(old_tgt_2, new_tgt)
        modified = True

    if modified:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file}")
