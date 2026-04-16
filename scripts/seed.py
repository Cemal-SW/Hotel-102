import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main_app.app import app
from core.models import db, Room, Experience, GalleryImage, Settings

rooms_data = [
    {
        "slug": "oceanfront-penthouse",
        "name": "Oceanfront Penthouse",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuAmA2Lr1zf7UTeyFp8C08jxercCvAwSEoXzLomIO2Dlv8vxR66qlQGBEQWZvMRryR93A_y78j5uwI0jFcY0g_RyWd8Jre0gYx1h4YnQhY9d1jJiVxTpxAscTWoV8R9akDrW1YsAOlEkcQfBkuMQNpMJlOZveOwK-1DQPikLoBzk8A8iCLpUJQIn_f67ezkv0898FUGvpvoLAQrRMXz5Qo4W3vwib7lbthPzFFoRPbtJ_v9-5x8RzCIjIPQRf7cQFS6bEhmFpiNBiCw",
        "desc": "Where the sky dissolves into the sea, a sanctuary designed for the limitless horizon. Featuring 360-degree glass walls, a private infinity pool that blends into the sky, and a dedicated 24-hour butler service.",
        "short_desc": "The crown jewel of The Shore. Featuring 360-degree glass walls, a private infinity pool that blends into the sky, and a dedicated 24-hour butler service.",
        "sqm": 450,
        "bed": "3 Bedrooms",
        "price": "4,500"
    },
    {
        "slug": "sunset-villa",
        "name": "Sunset Villa",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuCznEIeXgtRAv3h18v3C4Poq0KXP7YTU-gn3_WD2lzZ_zNV6IO6g2NGbHXzzAl6TXvE_nHjXqC5jULHyupL4W5lIGMa57gauWc0Iq6AmCyp34OuvT615KOXcZsGhdehXWqfijtK2S4sYW4ctYQ7zFOzfQy3q7wycQQFTvhaCRkszlJ1wPbgAs_zTvIOzaoGIg-5y7RyCDY8FvebP1QLMhkhgshWcMFe6B92ZVtk3XrZXrgyLlcv-zvyLiagI1qbv3m5gAGtqR83Ric",
        "desc": "Perched on the western tip, these villas offer the resort's most dramatic nightly spectacle.",
        "short_desc": "Perched on the western tip, these villas offer the resort's most dramatic nightly spectacle.",
        "sqm": 210,
        "bed": "1 Bedroom",
        "price": "1,250"
    },
    {
        "slug": "driftwood-suite",
        "name": "Driftwood Suite",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuCqY1ykyjkKrYR240UeBFeyCQITUUTXbzfMax6Kp0XHWlCdS1Dv9T9SGaKolzwcJL-_rYuAsKo4PGj_wWVO_-N_SljsANhzmJAC1-IWwVJRsQ6IeedHAyJk7gDgDiM1XiMRKeGgDChRJ5l2AwOKZnnD4hnpF_mfaohAwr3k3BIfbeQogdcJ6-33an9CEjoUHa7sTHL_5u4e58LIbAbc-X-2MvTg_tbSQ9o4jFjf7ydh6hb3DJQI-rZM8fo94YRMuPXyqG71_Bshyas",
        "desc": "Natural textures and organic shapes define this sanctuary of reclaimed luxury.",
        "short_desc": "Natural textures and organic shapes define this sanctuary of reclaimed luxury.",
        "sqm": 145,
        "bed": "Studio",
        "price": "850"
    },
    {
        "slug": "coral-garden-bungalow",
        "name": "Coral Garden Bungalow",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuC5FIcdXHuYWK_IhRrc3WlAy7FiWIZcnH6xZhlCKD84eoDaGHCB-ZkZhTwVhpqHMgc_sPdbyttkv4pR5CNFDlYpzaswba1rp_H1hVhnW1iN91oHfy3Xb0V8DlZYRzsKSGhEKJGCkQEB0tU3MmBEbFKp10pt48fKi5h62o1pG-wzu9Qzd4RQ-G7T4zeymVEj1hlYQ-fCpgTv6rs5ieHtOLEq1HEiYpJtaoPkPDPVw5qbNMn5pAFUQ6TfMsUKQAUm4DTtvAORqzZqrPg",
        "desc": "Tucked away in the tropical heart of the island, each bungalow is surrounded by rare flora and a private sand path to the lagoon.",
        "short_desc": "Tucked away in the tropical heart of the island, each bungalow is surrounded by rare flora and a private sand path to the lagoon.",
        "sqm": 180,
        "bed": "1 Bedroom",
        "price": "1,100"
    },
    {
        "slug": "azure-sands-loft",
        "name": "Azure Sands Loft",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuDzpbVodSm2u5JpzMaESyb-uxOqpDFfJupkQ5IYnmDRuXbJGKnYGbfC9ZeHj8wyTBn8e9jjIY7Ir5C41oOrJKRSfdo0_5J9wKW1yeWIy3WgMX2KwI0khuIja4E4sIGhpa-NMWRkYFaezcHgX3Kv4GtSdLB8Rfn3NcPcLjbhvaw0GrHcJqlSMnxlC3NtkiY5Uim3i0j_N704-7WO2K5hSU08v3n8BaJRsmIntOawMmmR9cU8gveZuU_4_9DSRdNQ2SgS5z7_kgLegsI",
        "desc": "Two-story vertical living with private sun terrace.",
        "short_desc": "Two-story vertical living with private sun terrace.",
        "sqm": 120,
        "bed": "1 Bedroom",
        "price": "920"
    },
    {
        "slug": "tidal-pool-villa",
        "name": "Tidal Pool Villa",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuBKaXlEc01cRiQLcs9f_QC-nqe4Rq0MtcOnmo1KUxj2fRYW3lwQ6-EWVZO7T0sLJhYgu__ym86lyRCrzVeTQ7wzSQWZxyOeF9fihljC1ivPivIbXDktUWVYdcIWyvbWlDepHufRGEzssjt_lbj8HsBOnQfpIOiVjXbwuD9FvhQGEhZeLPdEVV73AmNf3TXCa4gL17sXZi5Gpaw8mZuXuy5YElPYPP1IJWbD2QvOZ5VfTb59qElpWCZyJnuXb0xI6a5fH6-Zw22BsCo",
        "desc": "Modern architecture defined by the ocean's rhythm.",
        "short_desc": "Modern architecture defined by the ocean's rhythm.",
        "sqm": 190,
        "bed": "2 Bedrooms",
        "price": "1,450"
    },
    {
        "slug": "the-glass-house",
        "name": "The Glass House",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuDbL39abIGqSyqTXcUSdMEgRXcPkJpMZJN8I2OBRqX35v7L9nLqM5IqgT5bUsFOZTxLgAnx96GiK1IOUUmLNZMi-f_2hm8R3xbYMJ4-01CqMUB4zXlUSNeeitmDfJaXipSuC7YP1YEUFmK5hAl5Q4dOHwWTmzdMP4yX6higYM5pzWldATgf0LoU0eI06n3jKIk5j2a83NByphPMSMlaFCcAYeW-zKsBpK-oP0UFktgwaG7kouhtY0ornADDRzl4aWdrzg39uxcPoLQ",
        "desc": "A transparent masterpiece on the water's edge.",
        "short_desc": "A transparent masterpiece on the water's edge.",
        "sqm": 250,
        "bed": "2 Bedrooms",
        "price": "1,800"
    },
    {
        "slug": "sandbar-sanctuary",
        "name": "Sandbar Sanctuary",
        "hero_img": "https://lh3.googleusercontent.com/aida-public/AB6AXuAYEV9O6IUXPJkChIN7QD4OD5d8WxPeA4PteJMDEoCBoRBlCp4NLWP3Nr-7MJ0LUWkx-nHob0GeiJ-2yrGQ8X40rGkZKraeD-VC9eLjh7nfzENo30Fq4pnZI4OBIWx1Ax1mYz2iuVRd4WO9qQTR4HnnhaQaGCx3EcYfzr0Le0DC7V3gmBdSfoTOM8O7aVcuprswArIFZOURZXGGZgAT0yWdpbBT_kPesB4-wkH5bmJJCdTXz6NcvU86ljUiVFjHn80lCBgEnmfVmzQ",
        "desc": "Accessible only by a narrow boardwalk at low tide, this suite offers absolute isolation for those who seek to truly disappear.",
        "short_desc": "Accessible only by a narrow boardwalk at low tide, this suite offers absolute isolation for those who seek to truly disappear.",
        "sqm": 160,
        "bed": "1 Bedroom",
        "price": "1,600"
    }
]

experiences_data = [
    {
        "title": "Ethereal Spa",
        "description": "Holistic rituals using sea-minerals and botanical extracts.",
        "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuD3VCGM-A9FXhZO1xlnaVi-qQ9fJc5Smt9raszyBU0fFmA_H8QBReFs27jxIRtEt8VNq_nUnKMX4ZI__hnMuRxh_Y7ZnCfBWqN72WReRufZ2m82NLCGtwe07s96AhmvVBO0Sgv8Yoyu9l9-6M1FEgn96s2Jgzb97NAK7KDOVi0B9LozRwxXfI5K8EhKslFSXcH-QIJvjySpH3YugxDEqSFHD9HcMv1UdsF3CvtSe0AmGLUbLchiLPaR6x4KHMNGCdxzTaERZPBFPPp1",
    },
    {
        "title": "Sunset Mixology",
        "description": "Craft cocktails and panoramic views at twilight.",
        "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuDJfE2gCoXU4YEauWB4s-R4WMfM_JDYwyNkuF1WxjwvM5oyilqiE9z9aB2Dlc2D_Ly9xjXClOt_8pDJ7Sieu_fY6I22u698TtKoIX_YWkLT3mINz3UO02YPgXA7I9BfzcDDJpitQ3ALRjmDfJiZx-qUQPXzc8SxSWA24MwXdQA25NdGu3og9Pu77p2B_17-X1dhByLcl55hjwJgMX0JTmXBQKGI3uvKewMc1UF6MJuAH7ZOumxX6e0vHXPDSmqG0HIs2W-oyhooteZn",
    },
    {
        "title": "Private Dining",
        "description": "A bespoke dining experience exactly where you want it.",
        "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuDabxkoPefn2hPxrjI0DNjIujh6DRZrmSPED7qn3DGHPdCL89aocyN5VDvMxtsA-8_kxpi-1oHw90jYrwKhfiAK_t2eCkq-6DbjE4V6-LegVkWw0Rtl-mmlMk018Kr6Jm2O9_nzPymWJsMsLtt4yUkGnuy51Ok3PBnglzeqT8Ci_ZMgTIEMjq2zF5JGk7EY9lEFIeKJilbAEoJqz_QQihdm7GUS8FPks6p0CaoHz1WLp7iKLGksDPDW6KmOhFGkBdqlzWh781La9dFI",
    }
]

with app.app_context():
    db.create_all()

    # Seed Settings
    if not Settings.query.first():
        settings = Settings(
            hero_type='image', 
            hero_media='https://lh3.googleusercontent.com/aida-public/AB6AXuDzdQ2qqEWGIkkM88HzEuoncGLANE-eM1izr3oP2V_eWSe-lrdFvqpJPFBHdvcv96UKE5f14oq85ZjuGcok27IXdMRTMypy1Q7IyzEPtHtE8cTJQg9SZRCkmOLECdViTr7-exneP_a3KTpwqmjtXOkH7i62PXLSD5cCVqljuBCiiXatH88T53H9EdwLfSoqIMcX3gkmGsqC5sXOniRtJGLLVON0imdmKYBWQlftiLAwzUyTFGvDJbPlI4MPPYLC_FLkQEXfXgoTlZdB'
        )
        db.session.add(settings)

    # Add Rooms
    for i, data in enumerate(rooms_data):
        room = Room.query.filter_by(slug=data['slug']).first()
        if not room:
            room = Room(order_index=i, **data)
            db.session.add(room)

    # Add Experiences
    for i, data in enumerate(experiences_data):
        exp = Experience.query.filter_by(title=data['title']).first()
        if not exp:
            exp = Experience(order_index=i, **data)
            db.session.add(exp)

    db.session.commit()
    print("Database seeded completely!")
