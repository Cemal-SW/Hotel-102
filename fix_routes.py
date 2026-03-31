import os

files = ['about.html', 'contact.html', 'experiences.html', 'gallery.html']
base_dir = r'c:\Users\Msı\Desktop\Hotel-102\Hotel-102\templates'

for f in files:
    path = os.path.join(base_dir, f)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Replace main.js
        content = content.replace('src="main.js"', 'src="{{ url_for(\'static\', filename=\'main.js\') }}"')
        content = content.replace('href="animations.css"', 'href="{{ url_for(\'static\', filename=\'animations.css\') }}"')
        
        # Replace nav links securely
        content = content.replace('href="index.html"', 'href="{{ url_for(\'index\') }}"')
        content = content.replace('href="about.html"', 'href="{{ url_for(\'about\') }}"')
        content = content.replace('href="rooms.html"', 'href="{{ url_for(\'rooms\') }}"')
        content = content.replace('href="experiences.html"', 'href="{{ url_for(\'experiences\') }}"')
        content = content.replace('href="gallery.html"', 'href="{{ url_for(\'gallery\') }}"')
        content = content.replace('href="contact.html"', 'href="{{ url_for(\'contact\') }}"')
        
        with open(path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f'Updated {f}')
