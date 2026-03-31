import os
import re

with open('oceanfront-penthouse.html', 'r', encoding='utf-8') as f:
    template = f.read()

rooms = [
    {
        "filename": "sunset-villa.html",
        "name": "Sunset Villa",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuCznEIeXgtRAv3h18v3C4Poq0KXP7YTU-gn3_WD2lzZ_zNV6IO6g2NGbHXzzAl6TXvE_nHjXqC5jULHyupL4W5lIGMa57gauWc0Iq6AmCyp34OuvT615KOXcZsGhdehXWqfijtK2S4sYW4ctYQ7zFOzfQy3q7wycQQFTvhaCRkszlJ1wPbgAs_zTvIOzaoGIg-5y7RyCDY8FvebP1QLMhkhgshWcMFe6B92ZVtk3XrZXrgyLlcv-zvyLiagI1qbv3m5gAGtqR83Ric",
        "desc": "Perched on the western tip, these villas offer the resort's most dramatic nightly spectacle.",
        "sqm": "210",
        "bed": "1 Bedroom",
        "price": "1,250"
    },
    {
        "filename": "driftwood-suite.html",
        "name": "Driftwood Suite",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuCqY1ykyjkKrYR240UeBFeyCQITUUTXbzfMax6Kp0XHWlCdS1Dv9T9SGaKolzwcJL-_rYuAsKo4PGj_wWVO_-N_SljsANhzmJAC1-IWwVJRsQ6IeedHAyJk7gDgDiM1XiMRKeGgDChRJ5l2AwOKZnnD4hnpF_mfaohAwr3k3BIfbeQogdcJ6-33an9CEjoUHa7sTHL_5u4e58LIbAbc-X-2MvTg_tbSQ9o4jFjf7ydh6hb3DJQI-rZM8fo94YRMuPXyqG71_Bshyas",
        "desc": "Natural textures and organic shapes define this sanctuary of reclaimed luxury.",
        "sqm": "145",
        "bed": "Studio",
        "price": "850"
    },
    {
        "filename": "coral-garden-bungalow.html",
        "name": "Coral Garden Bungalow",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuC5FIcdXHuYWK_IhRrc3WlAy7FiWIZcnH6xZhlCKD84eoDaGHCB-ZkZhTwVhpqHMgc_sPdbyttkv4pR5CNFDlYpzaswba1rp_H1hVhnW1iN91oHfy3Xb0V8DlZYRzsKSGhEKJGCkQEB0tU3MmBEbFKp10pt48fKi5h62o1pG-wzu9Qzd4RQ-G7T4zeymVEj1hlYQ-fCpgTv6rs5ieHtOLEq1HEiYpJtaoPkPDPVw5qbNMn5pAFUQ6TfMsUKQAUm4DTtvAORqzZqrPg",
        "desc": "Tucked away in the tropical heart of the island, each bungalow is surrounded by rare flora and a private sand path to the lagoon.",
        "sqm": "180",
        "bed": "1 Bedroom",
        "price": "1,100"
    },
    {
        "filename": "azure-sands-loft.html",
        "name": "Azure Sands Loft",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuDzpbVodSm2u5JpzMaESyb-uxOqpDFfJupkQ5IYnmDRuXbJGKnYGbfC9ZeHj8wyTBn8e9jjIY7Ir5C41oOrJKRSfdo0_5J9wKW1yeWIy3WgMX2KwI0khuIja4E4sIGhpa-NMWRkYFaezcHgX3Kv4GtSdLB8Rfn3NcPcLjbhvaw0GrHcJqlSMnxlC3NtkiY5Uim3i0j_N704-7WO2K5hSU08v3n8BaJRsmIntOawMmmR9cU8gveZuU_4_9DSRdNQ2SgS5z7_kgLegsI",
        "desc": "Two-story vertical living with private sun terrace.",
        "sqm": "120",
        "bed": "1 Bedroom",
        "price": "920"
    },
    {
        "filename": "tidal-pool-villa.html",
        "name": "Tidal Pool Villa",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuBKaXlEc01cRiQLcs9f_QC-nqe4Rq0MtcOnmo1KUxj2fRYW3lwQ6-EWVZO7T0sLJhYgu__ym86lyRCrzVeTQ7wzSQWZxyOeF9fihljC1ivPivIbXDktUWVYdcIWyvbWlDepHufRGEzssjt_lbj8HsBOnQfpIOiVjXbwuD9FvhQGEhZeLPdEVV73AmNf3TXCa4gL17sXZi5Gpaw8mZuXuy5YElPYPP1IJWbD2QvOZ5VfTb59qElpWCZyJnuXb0xI6a5fH6-Zw22BsCo",
        "desc": "Modern architecture defined by the ocean's rhythm.",
        "sqm": "190",
        "bed": "2 Bedrooms",
        "price": "1,450"
    },
    {
        "filename": "the-glass-house.html",
        "name": "The Glass House",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuDbL39abIGqSyqTXcUSdMEgRXcPkJpMZJN8I2OBRqX35v7L9nLqM5IqgT5bUsFOZTxLgAnx96GiK1IOUUmLNZMi-f_2hm8R3xbYMJ4-01CqMUB4zXlUSNeeitmDfJaXipSuC7YP1YEUFmK5hAl5Q4dOHwWTmzdMP4yX6higYM5pzWldATgf0LoU0eI06n3jKIk5j2a83NByphPMSMlaFCcAYeW-zKsBpK-oP0UFktgwaG7kouhtY0ornADDRzl4aWdrzg39uxcPoLQ",
        "desc": "A transparent masterpiece on the water's edge.",
        "sqm": "250",
        "bed": "2 Bedrooms",
        "price": "1,800"
    },
    {
        "filename": "sandbar-sanctuary.html",
        "name": "Sandbar Sanctuary",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuAYEV9O6IUXPJkChIN7QD4OD5d8WxPeA4PteJMDEoCBoRBlCp4NLWP3Nr-7MJ0LUWkx-nHob0GeiJ-2yrGQ8X40rGkZKraeD-VC9eLjh7nfzENo30Fq4pnZI4OBIWx1Ax1mYz2iuVRd4WO9qQTR4HnnhaQaGCx3EcYfzr0Le0DC7V3gmBdSfoTOM8O7aVcuprswArIFZOURZXGGZgAT0yWdpbBT_kPesB4-wkH5bmJJCdTXz6NcvU86ljUiVFjHn80lCBgEnmfVmzQ",
        "desc": "Accessible only by a narrow boardwalk at low tide, this suite offers absolute isolation for those who seek to truly disappear.",
        "sqm": "160",
        "bed": "1 Bedroom",
        "price": "1,600"
    }
]

for r in rooms:
    content = template
    old_img = "https://lh3.googleusercontent.com/aida-public/AB6AXuAmA2Lr1zf7UTeyFp8C08jxercCvAwSEoXzLomIO2Dlv8vxR66qlQGBEQWZvMRryR93A_y78j5uwI0jFcY0g_RyWd8Jre0gYx1h4YnQhY9d1jJiVxTpxAscTWoV8R9akDrW1YsAOlEkcQfBkuMQNpMJlOZveOwK-1DQPikLoBzk8A8iCLpUJQIn_f67ezkv0898FUGvpvoLAQrRMXz5Qo4W3vwib7lbthPzFFoRPbtJ_v9-5x8RzCIjIPQRf7cQFS6bEhmFpiNBiCw"
    content = content.replace(old_img, r['hero_img'])
    content = content.replace('Oceanfront Penthouse', r['name'])
    content = content.replace('Where the sky dissolves into the sea, a sanctuary designed for the limitless horizon.', r['desc'])
    content = content.replace('4,500', r['price'])
    content = content.replace('450 SQM', f'{r["sqm"]} SQM')
    content = content.replace('3 Bedrooms', r['bed'])
    
    with open(r['filename'], 'w', encoding='utf-8') as n:
        n.write(content)

with open('rooms.html', 'r', encoding='utf-8') as f:
    html = f.read()

rooms_to_link = [
    ("Sunset Villa", "sunset-villa.html"),
    ("Driftwood Suite", "driftwood-suite.html"),
    ("Coral Garden Bungalow", "coral-garden-bungalow.html"),
    ("Azure Sands Loft", "azure-sands-loft.html"),
    ("Tidal Pool Villa", "tidal-pool-villa.html"),
    ("The Glass House", "the-glass-house.html"),
    ("Sandbar Sanctuary", "sandbar-sanctuary.html")
]

for name, link in rooms_to_link:
    pattern = rf'(>.*?(?:{name}).*?<\/h[234]>)(.*?)(<button[^>]*class="view-more-btn"[^>]*>View more -&gt;<\/button>)'
    match = re.search(pattern, html, flags=re.DOTALL)
    if match:
        heading = match.group(1)
        middle = match.group(2)
        button = match.group(3)
        replacement = heading + middle + f'<a href="{link}" class="view-more-btn">View more -&gt;</a>'
        html = html.replace(match.group(0), replacement)

with open('rooms.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("GENERATED SUCCESSFULLY")
