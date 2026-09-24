"""
ai_recommender.py
Intelligent Keyword & Market Recommender with Daily Google Live Sync,
Hierarchical Category & Sub-Category Separation, and Specialized
Real Estate Plot Business Intelligence for Bihar & Jharkhand.
"""

import os
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
import random
import re
import threading

CACHE_FILE = os.path.join(os.path.dirname(__file__), "google_keywords_cache.json")

# In-memory cache & background sync state for instantaneous category switching
_MEM_CACHE = None
_SYNC_LOCK = threading.Lock()
_SYNC_IN_PROGRESS = False

# Regional Hubs and Commercial Centers for Bihar & Jharkhand
REGIONS = {
    "bihar": {
        "name": "Bihar",
        "flag": "🟢",
        "cities": [
            {"name": "Patna", "tier": "Metro Capital", "hubs": ["Bihta", "Danapur", "Boring Road", "Kankarbagh", "Bailey Road", "Saguna More", "Shivala", "Patna Ring Road", "Exhibition Road", "Fatuha"]},
            {"name": "Muzaffarpur", "tier": "North Bihar Commercial Hub", "hubs": ["Bhagwanpur", "Mithanpura", "Sutapatti", "Gobarsahi", "Bypass Road"]},
            {"name": "Gaya", "tier": "Tourism & Commercial Center", "hubs": ["Bodh Gaya", "Civil Lines", "Dobhi Highway", "GB Road"]},
            {"name": "Bhagalpur", "tier": "Silk & Trade City", "hubs": ["Adampur", "Zero Mile", "Tilkamanjhi", "Bypass Road"]},
            {"name": "Darbhanga", "tier": "Mithila Airport Hub", "hubs": ["Laheriasarai", "Airport Road", "Tower Chowk"]},
            {"name": "Purnia", "tier": "Seemanchal Agro Hub", "hubs": ["Line Bazar", "Bhatta Bazar", "Gulabbagh"]},
            {"name": "Begusarai", "tier": "Industrial Capital", "hubs": ["Barauni", "Traffic Chowk", "NH-31 Corridor"]},
            {"name": "Ara", "tier": "Bhojpur Commercial Hub", "hubs": ["Gopali Chowk", "Arrah-Patna 4 Lane Road"]},
            {"name": "Bihar Sharif", "tier": "Nalanda Trade Hub", "hubs": ["Ranchi Road", "Hospital More", "NH-20"]},
            {"name": "Samastipur", "tier": "Railway & Agro Trade", "hubs": ["Tajpur Road", "Station Road"]},
            {"name": "Motihari", "tier": "Champaran Center", "hubs": ["Main Road", "Chhatauni Bypass"]}
        ]
    },
    "jharkhand": {
        "name": "Jharkhand",
        "flag": "🟠",
        "cities": [
            {"name": "Ranchi", "tier": "Capital & IT Hub", "hubs": ["Ring Road", "Kathal More", "Tupudana", "Namkum", "Ormanjhi", "Lalpur", "Main Road", "Harmu", "Bariatu", "Ratu Road", "Doranda"]},
            {"name": "Jamshedpur", "tier": "Industrial & Steel City", "hubs": ["Bistupur", "Sakchi", "Dimna Road", "Mango", "Gamharia", "Adityapur Industrial Area", "Telco"]},
            {"name": "Dhanbad", "tier": "Coal & Energy Capital", "hubs": ["Bank More", "Govindpur GT Road", "Saraidhela", "Barwadda Bypass", "Hirapur"]},
            {"name": "Bokaro Steel City", "tier": "Steel & Education City", "hubs": ["Sector 4", "Chas Highway Corridor", "Sector 1"]},
            {"name": "Deoghar", "tier": "Spiritual Tourism & AIIMS Hub", "hubs": ["AIIMS Road", "Tower Chowk", "Castairs Town", "Jasidih"]},
            {"name": "Hazaribagh", "tier": "Education & Transit Hub", "hubs": ["Malviya Marg", "Korrah", "NH-33 Bypass"]},
            {"name": "Giridih", "tier": "Mica & Steel Trade", "hubs": ["Makatpur", "Bada Chowk", "Pachamba"]},
            {"name": "Ramgarh", "tier": "Industrial & Mineral Belt", "hubs": ["Subhash Chowk", "Gola Road", "NH-33"]},
            {"name": "Chaibasa", "tier": "Kolhan Mining & Trade", "hubs": ["Sadik Bazar", "Post Office Chowk"]},
            {"name": "Medininagar", "tier": "Palamu Regional Hub", "hubs": ["Six Corner", "Kizirbagh"]}
        ]
    }
}

# Super Categories and Sub-Categories with deep Real Estate Plot Specialization
BUSINESS_CATEGORIES = [
    {
        "id": "realestate_plots",
        "name": "Real Estate & Plots",
        "icon": "🏡",
        "color": "#10b981",
        "featured": True,
        "description": "Your Primary Focus: High-ticket residential, commercial, industrial plots & land corridors in Bihar & Jharkhand",
        "sub_categories": [
            {
                "id": "res_plots",
                "name": "Residential Plots & Colonies",
                "icon": "🏘️",
                "keywords": [
                    {"keyword": "Residential Plots for Sale", "tag": "🔥 High Demand", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Jamshedpur"]},
                    {"keyword": "Gated Community Plots", "tag": "⭐ Premium", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Dhanbad", "Jamshedpur"]},
                    {"keyword": "Corner Plots in Gated Society", "tag": "💎 Fast Seller", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Bokaro"]},
                    {"keyword": "Affordable Housing Plots", "tag": "🚀 Bulk Volume", "ticket": "Mid Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Gaya"]},
                    {"keyword": "Duplex Land and Villa Plots", "tag": "👑 Luxury", "ticket": "Ultra High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Immediate Registry Plots", "tag": "⚡ High Trust", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Dhanbad", "Bhagalpur"]}
                ]
            },
            {
                "id": "comm_plots",
                "name": "Commercial & Highway Land",
                "icon": "🏢",
                "keywords": [
                    {"keyword": "Commercial Land for Sale", "tag": "💰 Ultra High Ticket", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Dhanbad"]},
                    {"keyword": "Highway Facing Plots on 4 Lane", "tag": "🛣️ Prime Commercial", "ticket": "Ultra High Ticket", "source": "google", "cities": ["Patna", "Muzaffarpur", "Ranchi", "Begusarai"]},
                    {"keyword": "Petrol Pump Suitable Land", "tag": "⛽ High Investor", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Gaya", "Ranchi", "Dhanbad"]},
                    {"keyword": "Hospital and School Land Plots", "tag": "🏥 Institutional", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Dhanbad"]},
                    {"keyword": "Commercial Market Complex Land", "tag": "🛍️ B2B Builder", "ticket": "Ultra High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Bokaro"]}
                ]
            },
            {
                "id": "corridor_plots",
                "name": "High-Growth Corridors",
                "icon": "📍",
                "keywords": [
                    {"keyword": "Bihta Airport Road Plots", "tag": "🔥 #1 Hotspot Bihar", "ticket": "High Ticket", "source": "google", "cities": ["Patna"]},
                    {"keyword": "Patna Ring Road Plots", "tag": "🚀 10x Appreciation", "ticket": "High Ticket", "source": "google", "cities": ["Patna"]},
                    {"keyword": "Danapur Shivala Khagaul Road Plots", "tag": "⭐ Prime Metro", "ticket": "High Ticket", "source": "google", "cities": ["Patna"]},
                    {"keyword": "Ranchi Ring Road Plots", "tag": "🔥 #1 Hotspot Jharkhand", "ticket": "High Ticket", "source": "google", "cities": ["Ranchi"]},
                    {"keyword": "Tupudana Kathal More Plots", "tag": "📈 High Growth", "ticket": "High Ticket", "source": "google", "cities": ["Ranchi"]},
                    {"keyword": "Jamshedpur Dimna Road Mango Plots", "tag": "🏙️ Steel Belt", "ticket": "High Ticket", "source": "google", "cities": ["Jamshedpur"]},
                    {"keyword": "Dhanbad Govindpur GT Road Plots", "tag": "🛣️ Highway Hub", "ticket": "High Ticket", "source": "google", "cities": ["Dhanbad"]},
                    {"keyword": "Deoghar AIIMS Road Land", "tag": "🩺 Medical Corridor", "ticket": "High Ticket", "source": "google", "cities": ["Deoghar"]}
                ]
            },
            {
                "id": "rera_legal",
                "name": "RERA Approved & Legal Land",
                "icon": "🏛️",
                "keywords": [
                    {"keyword": "RERA Approved Plots", "tag": "✅ 100% Verified", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Muzaffarpur"]},
                    {"keyword": "RERA Registered Township Plots", "tag": "🛡️ Zero Risk", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Dhanbad"]},
                    {"keyword": "Dakhil Kharij Mutated Land Plots", "tag": "📜 Clear Title", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Gaya", "Muzaffarpur"]},
                    {"keyword": "Bank Loan Approved Plots", "tag": "🏦 Easy EMI", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Bokaro", "Jamshedpur"]}
                ]
            },
            {
                "id": "brokers_partners",
                "name": "Land Brokers & Channel Partners",
                "icon": "🤝",
                "keywords": [
                    {"keyword": "Real Estate Agents and Property Dealers", "tag": "🤝 Network Leads", "ticket": "B2B Partner", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Jamshedpur", "Dhanbad"]},
                    {"keyword": "Land Colonizers and Developers", "tag": "🏗️ Bulk Plots", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Ranchi", "Gaya", "Bokaro"]},
                    {"keyword": "Property Resale Consultants", "tag": "🔄 Fast Liquidity", "ticket": "Commission", "source": "google", "cities": ["Patna", "Ranchi", "Dhanbad"]},
                    {"keyword": "Plot Channel Partners and Brokers", "tag": "💼 Sales Network", "ticket": "B2B Partner", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]}
                ]
            },
            {
                "id": "ind_warehouse",
                "name": "Industrial & Warehouse Land",
                "icon": "🏭",
                "keywords": [
                    {"keyword": "BIADA Industrial Land Plots", "tag": "🏭 Gov Industrial", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Begusarai", "Muzaffarpur", "Bokaro"]},
                    {"keyword": "Warehouse and Godown Land for Sale", "tag": "📦 Logistics Boom", "ticket": "Ultra High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Dhanbad"]},
                    {"keyword": "Factory and Manufacturing Land", "tag": "⚙️ Heavy Industry", "ticket": "Enterprise", "source": "google", "cities": ["Jamshedpur", "Ramgarh", "Bokaro", "Begusarai"]},
                    {"keyword": "Cold Storage Suitable Land", "tag": "❄️ Agro Industrial", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Muzaffarpur", "Purnia", "Samastipur"]}
                ]
            },
            {
                "id": "target_buyers",
                "name": "High-Ticket Plot Buyer Niches",
                "icon": "🎯",
                "keywords": [
                    {"keyword": "Doctors and Surgeons Clinic", "tag": "🩺 High Net Worth Plot Buyers", "ticket": "HNWI Buyers", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Dhanbad"]},
                    {"keyword": "Coaching Institute Directors", "tag": "🎓 Institutional Plot Buyers", "ticket": "HNWI Buyers", "source": "google", "cities": ["Patna", "Ranchi", "Bokaro", "Gaya"]},
                    {"keyword": "Building and Civil Contractors", "tag": "🛠️ Builder & Investor", "ticket": "HNWI Buyers", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Dhanbad"]},
                    {"keyword": "Chartered Accountants CA Firms", "tag": "💼 Investor Advisors", "ticket": "HNWI Buyers", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Jewelry Showroom Owners", "tag": "💎 Ultra HNW Investor", "ticket": "HNWI Buyers", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Jamshedpur"]}
                ]
            }
        ]
    },
    {
        "id": "healthcare",
        "name": "Doctors & Healthcare",
        "icon": "🏥",
        "color": "#ef4444",
        "featured": False,
        "description": "Clinics, Hospitals, Doctors, Diagnostics and Medical Centers",
        "sub_categories": [
            {
                "id": "specialist_doctors",
                "name": "Specialist Doctors & Clinics",
                "icon": "🩺",
                "keywords": [
                    {"keyword": "Best Doctor for Bone", "tag": "🦴 High Search Intent", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Jamshedpur", "Dhanbad"]},
                    {"keyword": "Best Orthopedic Doctor", "tag": "⭐ Top Rated", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Bhagalpur"]},
                    {"keyword": "Best Bone Specialist Doctor", "tag": "🩺 High Value", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Gaya", "Dhanbad"]},
                    {"keyword": "Best Knee Replacement Doctor", "tag": "🏥 Super Specialist", "ticket": "Ultra High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Best Joint Pain Specialist Doctor", "tag": "⚡ High Demand", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur"]},
                    {"keyword": "Orthopedic Clinic", "tag": "🔥 High Demand", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Jamshedpur"]},
                    {"keyword": "Dental Clinic", "tag": "🦷 High Volume", "ticket": "Mid Ticket", "source": "google", "cities": ["Patna", "Dhanbad", "Ranchi", "Gaya"]},
                    {"keyword": "Gynecologist Clinic", "tag": "⭐ High Intent", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Bokaro", "Muzaffarpur", "Jamshedpur"]},
                    {"keyword": "Neuro Psychiatrist Clinic", "tag": "🧠 Specialized", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur"]},
                    {"keyword": "Eye Hospital and Lasik", "tag": "👁️ High Conversion", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Jamshedpur", "Gaya", "Dhanbad"]},
                    {"keyword": "Pediatrician Clinic", "tag": "👶 High Demand", "ticket": "Recurring", "source": "google", "cities": ["Ranchi", "Patna", "Bokaro", "Bhagalpur"]}
                ]
            },
            {
                "id": "diagnostic_labs",
                "name": "Diagnostics & Pathology",
                "icon": "🔬",
                "keywords": [
                    {"keyword": "Pathology Labs", "tag": "🔬 B2B & Retail", "ticket": "Recurring", "source": "google", "cities": ["Patna", "Ranchi", "Bhagalpur", "Dhanbad"]},
                    {"keyword": "Diagnostic and Ultrasound Center", "tag": "⚡ High Volume", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Muzaffarpur", "Ranchi", "Dhanbad"]},
                    {"keyword": "Ayurvedic Treatment Clinic", "tag": "🌿 Holistic", "ticket": "Mid Ticket", "source": "google", "cities": ["Deoghar", "Gaya", "Patna", "Ranchi"]}
                ]
            }
        ]
    },
    {
        "id": "fitness_gyms",
        "name": "Gyms, Fitness & Wellness",
        "icon": "🏋️",
        "color": "#f97316",
        "featured": True,
        "description": "Top-rated Gyms, Personal Trainers, Unisex Fitness Centers, Crossfit & Yoga Studios",
        "sub_categories": [
            {
                "id": "gyms_trainers",
                "name": "Best Gyms & Fitness Centers",
                "icon": "💪",
                "keywords": [
                    {"keyword": "Best Gym", "tag": "🔥 #1 Search Intent", "ticket": "High Volume", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Jamshedpur", "Dhanbad", "Gaya"]},
                    {"keyword": "Best Gym with Personal Trainer", "tag": "⭐ Premium Fitness", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Dhanbad"]},
                    {"keyword": "Best Unisex Gym", "tag": "🏋️ High Footfall", "ticket": "Recurring", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Bokaro"]},
                    {"keyword": "Best Gym for Weight Loss", "tag": "🎯 High Intent", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Luxury Fitness Club and Gym", "tag": "💎 Elite Members", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "CrossFit and Strength Training Gym", "tag": "⚡ Modern Athletic", "ticket": "High Margin", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]}
                ]
            },
            {
                "id": "yoga_wellness",
                "name": "Yoga, Zumba & Nutrition",
                "icon": "🧘",
                "keywords": [
                    {"keyword": "Best Yoga Classes and Studio", "tag": "🧘 Wellness", "ticket": "Recurring", "source": "google", "cities": ["Patna", "Ranchi", "Deoghar", "Jamshedpur"]},
                    {"keyword": "Zumba and Aerobics Dance Classes", "tag": "💃 High Demand", "ticket": "Recurring", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur"]},
                    {"keyword": "Dietitian and Nutritionist Clinic", "tag": "🥗 Consultation", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Dhanbad"]}
                ]
            }
        ]
    },
    {
        "id": "coaching",
        "name": "Education & Coaching",
        "icon": "🎓",
        "color": "#a855f7",
        "featured": False,
        "description": "IIT JEE, NEET, UPSC, BPSC, JPSC, Tuition & Skills Institutes",
        "sub_categories": [
            {
                "id": "competitive_exams",
                "name": "Competitive Exam Coaching",
                "icon": "📚",
                "keywords": [
                    {"keyword": "IIT JEE & NEET Coaching", "tag": "🔥 Massive Volume", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Bokaro", "Gaya"]},
                    {"keyword": "UPSC & BPSC Coaching", "tag": "🏛️ Gov Exam Hub", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Muzaffarpur", "Bhagalpur"]},
                    {"keyword": "JPSC & SSC Coaching", "tag": "📚 High Demand", "ticket": "Mid Ticket", "source": "google", "cities": ["Ranchi", "Dhanbad", "Jamshedpur", "Hazaribagh"]},
                    {"keyword": "Banking & Railway Exam Academy", "tag": "🎯 Bulk Leads", "ticket": "Mid Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Dhanbad"]}
                ]
            },
            {
                "id": "professional_tuitions",
                "name": "Commerce, Tech & Tuitions",
                "icon": "💻",
                "keywords": [
                    {"keyword": "Commerce & CA Foundation Classes", "tag": "💼 Professional", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Spoken English and IELTS Institute", "tag": "🗣️ High Conversion", "ticket": "Mid Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Dhanbad", "Muzaffarpur"]},
                    {"keyword": "Coding & Web Development Institute", "tag": "💻 IT Skills", "ticket": "High Ticket", "source": "google", "cities": ["Ranchi", "Patna", "Jamshedpur"]},
                    {"keyword": "Class 9-12 Science Tuition Center", "tag": "📐 Local Recurring", "ticket": "Recurring", "source": "google", "cities": ["Patna", "Bokaro", "Ranchi", "Ara"]}
                ]
            }
        ]
    },
    {
        "id": "construction_building",
        "name": "Building & Construction",
        "icon": "🏗️",
        "color": "#3b82f6",
        "featured": False,
        "description": "Builders, Architects, Civil Contractors, TMT Steel & Building Materials",
        "sub_categories": [
            {
                "id": "builders_architects",
                "name": "Builders & Architects",
                "icon": "📐",
                "keywords": [
                    {"keyword": "Builders and Developers", "tag": "💰 Ultra High Ticket", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Dhanbad"]},
                    {"keyword": "Interior Designer", "tag": "🎨 High Margin", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Bokaro"]},
                    {"keyword": "Architects and Structural Engineers", "tag": "📐 B2B Verified", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Modular Kitchen Showroom", "tag": "✨ Luxury Home", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]}
                ]
            },
            {
                "id": "building_materials",
                "name": "Building Materials & Contractors",
                "icon": "🧱",
                "keywords": [
                    {"keyword": "TMT Steel and Cement Dealer", "tag": "🏗️ Wholesale B2B", "ticket": "Bulk Volume", "source": "google", "cities": ["Patna", "Begusarai", "Jamshedpur", "Ramgarh"]},
                    {"keyword": "Civil Building Contractors", "tag": "🛠️ Project Leads", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Ranchi", "Bokaro", "Dhanbad"]},
                    {"keyword": "Hardware and Sanitaryware Wholesalers", "tag": "🔩 Construction Supply", "ticket": "Bulk Volume", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Dhanbad"]}
                ]
            }
        ]
    },
    {
        "id": "finance_legal",
        "name": "Finance, CA & Legal",
        "icon": "⚖️",
        "color": "#0ea5e9",
        "featured": False,
        "description": "Chartered Accountants, GST Tax Consultants, Lawyers & Financial Services",
        "sub_categories": [
            {
                "id": "ca_tax",
                "name": "CA & Tax Consultants",
                "icon": "📊",
                "keywords": [
                    {"keyword": "Chartered Accountant CA Firm", "tag": "💼 B2B Core", "ticket": "High Retainer", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Dhanbad"]},
                    {"keyword": "GST and Income Tax Consultant", "tag": "📊 High Volume", "ticket": "Recurring", "source": "google", "cities": ["Patna", "Muzaffarpur", "Ranchi", "Bhagalpur"]},
                    {"keyword": "Business Registration and Trademark Consultant", "tag": "🚀 Startup Hub", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]}
                ]
            },
            {
                "id": "legal_loans",
                "name": "Legal & Project Loans",
                "icon": "🏛️",
                "keywords": [
                    {"keyword": "Corporate Lawyer and Advocates", "tag": "⚖️ High Value", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Dhanbad"]},
                    {"keyword": "Business Loan and Project Finance Consultant", "tag": "💳 Financial B2B", "ticket": "Commission", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Dhanbad"]}
                ]
            }
        ]
    },
    {
        "id": "automobile",
        "name": "Automobile & Garages",
        "icon": "🚗",
        "color": "#f59e0b",
        "featured": False,
        "description": "Car Showrooms, Multi-Brand Garages, Detailing & Auto Spares",
        "sub_categories": [
            {
                "id": "dealers_garages",
                "name": "Showrooms & Garages",
                "icon": "🔧",
                "keywords": [
                    {"keyword": "Car Showrooms", "tag": "🚗 Dealerships", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Jamshedpur"]},
                    {"keyword": "Multi Brand Car Service Garage", "tag": "🔧 High Demand", "ticket": "Recurring", "source": "google", "cities": ["Patna", "Ranchi", "Dhanbad", "Bokaro"]},
                    {"keyword": "Car Detailing Ceramic Coating PPF", "tag": "✨ Premium Auto", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]}
                ]
            },
            {
                "id": "auto_parts",
                "name": "Auto Spares & Tyres",
                "icon": "⚙️",
                "keywords": [
                    {"keyword": "Auto Spare Parts Wholesaler", "tag": "📦 B2B Traders", "ticket": "Bulk Volume", "source": "google", "cities": ["Patna", "Jamshedpur", "Ranchi", "Muzaffarpur"]},
                    {"keyword": "Tyre and Battery Distributor", "tag": "⚡ Fast Moving", "ticket": "B2B Recurring", "source": "google", "cities": ["Patna", "Dhanbad", "Ranchi", "Gaya"]},
                    {"keyword": "Commercial Vehicle Truck Spares", "tag": "🚛 Heavy Fleet", "ticket": "Bulk Volume", "source": "google", "cities": ["Jamshedpur", "Ramgarh", "Dhanbad", "Begusarai"]}
                ]
            }
        ]
    },
    {
        "id": "hospitality_events",
        "name": "Banquets & Hospitality",
        "icon": "🏨",
        "color": "#ec4899",
        "featured": False,
        "description": "Marriage Banquet Halls, Hotels, Wedding Caterers & Event Planners",
        "sub_categories": [
            {
                "id": "weddings_banquets",
                "name": "Marriage Banquets & Caterers",
                "icon": "🎉",
                "keywords": [
                    {"keyword": "Marriage Banquet Hall", "tag": "🎉 Huge Wedding Spend", "ticket": "Ultra High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Dhanbad", "Gaya"]},
                    {"keyword": "Catering Services for Weddings", "tag": "🍽️ High Ticket Events", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Bhagalpur"]},
                    {"keyword": "Event Management Company", "tag": "🎪 Corporate & Weddings", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Candid Wedding Photographers", "tag": "📸 Premium Clients", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Dhanbad"]}
                ]
            },
            {
                "id": "hotels_dining",
                "name": "Hotels & Fine Dining",
                "icon": "🛎️",
                "keywords": [
                    {"keyword": "Luxury and Boutique Hotels", "tag": "🛎️ Corporate & Tourism", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Ranchi", "Deoghar", "Bodh Gaya", "Jamshedpur"]},
                    {"keyword": "Fine Dine Restaurant and Cafe", "tag": "☕ Youth & Family", "ticket": "Daily Footfall", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Bokaro"]}
                ]
            }
        ]
    },
    {
        "id": "wholesale_mandi",
        "name": "Wholesale & Mandis",
        "icon": "🏭",
        "color": "#64748b",
        "featured": False,
        "description": "FMCG Distributors, Mandi Grain Traders, Electrical & Mining Suppliers",
        "sub_categories": [
            {
                "id": "fmcg_grain",
                "name": "FMCG & Agro Mandis",
                "icon": "🌾",
                "keywords": [
                    {"keyword": "FMCG Distributors and Wholesalers", "tag": "📦 High Turnover", "ticket": "Bulk Volume", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Dhanbad"]},
                    {"keyword": "Grain and Rice Mandi Traders", "tag": "🌾 Agro Wholesale", "ticket": "Bulk Volume", "source": "google", "cities": ["Patna", "Purnia", "Muzaffarpur", "Buxar"]}
                ]
            },
            {
                "id": "industrial_b2b",
                "name": "Industrial & Mining B2B",
                "icon": "⛏️",
                "keywords": [
                    {"keyword": "Electrical Cable and Switchgear Wholesalers", "tag": "⚡ B2B Supply", "ticket": "Bulk Volume", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Plastic and Packaging Material Manufacturers", "tag": "🏭 Industrial Supply", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Jamshedpur", "Bokaro", "Begusarai"]},
                    {"keyword": "Mining Equipment and Spares Suppliers", "tag": "⛏️ Heavy Mineral", "ticket": "High Ticket", "source": "google", "cities": ["Dhanbad", "Ramgarh", "Chaibasa", "Ranchi"]}
                ]
            }
        ]
    },
    {
        "id": "retail_jewelry",
        "name": "Retail & Jewelry",
        "icon": "🛍️",
        "color": "#eab308",
        "featured": False,
        "description": "Jewelry Showrooms, Bridal Wear, Electronics, Furniture & Opticals",
        "sub_categories": [
            {
                "id": "jewelry_fashion",
                "name": "Jewelry & Bridal Wear",
                "icon": "💎",
                "keywords": [
                    {"keyword": "Jewelry Showrooms", "tag": "💎 High Net Worth", "ticket": "Ultra High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Jamshedpur", "Dhanbad"]},
                    {"keyword": "Bridal Saree and Ethnic Wear Showroom", "tag": "👗 Wedding Shopping", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Bhagalpur", "Muzaffarpur"]}
                ]
            },
            {
                "id": "consumer_retail",
                "name": "Electronics & Home Retail",
                "icon": "📱",
                "keywords": [
                    {"keyword": "Electronics and Mobile Store", "tag": "📱 High Tech Retail", "ticket": "Mid Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Dhanbad", "Gaya"]},
                    {"keyword": "Wooden and Modern Furniture Showroom", "tag": "🛋️ Home Decor", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur", "Bokaro"]},
                    {"keyword": "Optician and Designer Eyewear Store", "tag": "👓 Healthcare Retail", "ticket": "Mid Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Dhanbad"]}
                ]
            }
        ]
    },
    {
        "id": "tech_digital",
        "name": "IT & Digital Services",
        "icon": "💻",
        "color": "#06b6d4",
        "featured": False,
        "description": "Digital Marketing Agencies, Web Developers, CCTV Security & Software",
        "sub_categories": [
            {
                "id": "agency_software",
                "name": "Digital Agencies & Web Dev",
                "icon": "🌐",
                "keywords": [
                    {"keyword": "Digital Marketing Agency", "tag": "🚀 Growth Clients", "ticket": "High Retainer", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Website and App Development Company", "tag": "🌐 B2B Tech", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Software Solutions Provider", "tag": "💾 Enterprise IT", "ticket": "Enterprise", "source": "google", "cities": ["Ranchi", "Patna", "Jamshedpur"]}
                ]
            },
            {
                "id": "security_hardware",
                "name": "CCTV & Computer Hardware",
                "icon": "📹",
                "keywords": [
                    {"keyword": "CCTV Security Camera Wholesaler and Installer", "tag": "📹 High Demand", "ticket": "Commercial", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Dhanbad"]},
                    {"keyword": "Computer Hardware and Networking Wholesaler", "tag": "🖥️ Institutional", "ticket": "Bulk Volume", "source": "google", "cities": ["Patna", "Ranchi", "Dhanbad"]}
                ]
            }
        ]
    },
    {
        "id": "agri_solar",
        "name": "Agri & Solar Energy",
        "icon": "☀️",
        "color": "#16a34a",
        "featured": False,
        "description": "Solar Panel Installers, Cold Storages, Farm Machinery, Fertilizer Dealers & Seed Distributors",
        "sub_categories": [
            {
                "id": "solar_power",
                "name": "Solar Energy & EPC",
                "icon": "⚡",
                "keywords": [
                    {"keyword": "Solar Panel Dealers and Installers", "tag": "⚡ High Subsidy", "ticket": "High Ticket", "source": "google", "cities": ["Patna", "Ranchi", "Muzaffarpur", "Gaya", "Dhanbad"]},
                    {"keyword": "Rooftop Solar EPC Contractors", "tag": "🏢 B2B Solar", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Ranchi", "Jamshedpur"]},
                    {"keyword": "Solar Water Pump Distributors", "tag": "🌾 Agri Solar", "ticket": "Mid Ticket", "source": "google", "cities": ["Patna", "Muzaffarpur", "Purnia", "Ranchi"]}
                ]
            },
            {
                "id": "agro_machinery",
                "name": "Agro Machinery & Cold Storage",
                "icon": "🚜",
                "keywords": [
                    {"keyword": "Tractor and Harvester Showroom", "tag": "🚜 High Investment", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Muzaffarpur", "Begusarai", "Purnia", "Gaya"]},
                    {"keyword": "Cold Storage Facility and Owners", "tag": "❄️ Agro Industrial", "ticket": "Enterprise", "source": "google", "cities": ["Patna", "Muzaffarpur", "Purnia", "Samastipur"]},
                    {"keyword": "Fertilizers and Seeds Wholesalers", "tag": "🌾 Bulk Volume", "ticket": "Bulk Volume", "source": "google", "cities": ["Patna", "Purnia", "Muzaffarpur", "Ranchi", "Bhagalpur"]}
                ]
            }
        ]
    }
]

def fetch_live_google_suggestions(query_seed, country="in", lang="en"):
    """
    Fetch live real-time Google search suggestions from Google's India endpoint.
    """
    encoded_query = urllib.parse.quote_plus(query_seed)
    url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={encoded_query}&gl={country}&hl={lang}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3.5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 1:
                return data[1]  # list of suggested strings
    except Exception as e:
        # Fallback gracefully
        pass
    return []

def get_cached_google_keywords():
    """
    Instantly returns cached Google keywords from memory or disk (<1ms).
    If cache is missing or stale (date != today), spawns a background thread
    to refresh without blocking user requests or UI switching.
    """
    global _MEM_CACHE, _SYNC_IN_PROGRESS
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1. Check in-memory cache
    if _MEM_CACHE and _MEM_CACHE.get("keywords"):
        if _MEM_CACHE.get("date") != today_str and not _SYNC_IN_PROGRESS:
            _trigger_background_sync()
        return _MEM_CACHE.get("keywords", [])

    # 2. Check disk cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached.get("keywords"):
                    _MEM_CACHE = cached
                    if cached.get("date") != today_str and not _SYNC_IN_PROGRESS:
                        _trigger_background_sync()
                    return cached.get("keywords", [])
        except Exception:
            pass

    # 3. If no cache exists, trigger background sync
    if not _SYNC_IN_PROGRESS:
        _trigger_background_sync()
    return []

def _trigger_background_sync():
    """Trigger Google keywords sync in a background daemon thread."""
    global _SYNC_IN_PROGRESS
    with _SYNC_LOCK:
        if _SYNC_IN_PROGRESS:
            return
        _SYNC_IN_PROGRESS = True
    
    t = threading.Thread(target=_bg_sync_worker, daemon=True)
    t.start()

def _bg_sync_worker():
    global _SYNC_IN_PROGRESS
    try:
        sync_google_keywords(force=True)
    except Exception as e:
        print(f"[Google Sync Background Error] {e}")
    finally:
        _SYNC_IN_PROGRESS = False

def sync_google_keywords(force=False):
    """
    Daily Google Live Keyword Sync.
    Fetches live suggestions from Google. Updates _MEM_CACHE and CACHE_FILE.
    """
    global _MEM_CACHE
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if not force:
        if _MEM_CACHE and _MEM_CACHE.get("date") == today_str and _MEM_CACHE.get("keywords"):
            return _MEM_CACHE
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if cached.get("date") == today_str and cached.get("keywords"):
                        _MEM_CACHE = cached
                        return cached
            except Exception:
                pass

    # Seeds focusing primarily on Real Estate Plots in Bihar & Jharkhand + other sectors
    seeds = [
        "plots for sale in patna",
        "residential plots in ranchi",
        "plots in bihta patna",
        "rera approved plots in patna",
        "commercial land for sale in ranchi",
        "plots in ring road ranchi",
        "industrial land in bihar",
        "property dealers in patna",
        "plots in jamshedpur",
        "plots in dhanbad",
        "marriage banquet hall in patna",
        "doctors clinic in patna",
        "best doctor for bone in patna",
        "best orthopedic doctor in patna",
        "best doctor for bone in ranchi",
        "best gym in patna",
        "best gym in ranchi",
        "coaching institute in patna"
    ]

    synced_items = []
    seen = set()

    for seed in seeds:
        suggestions = fetch_live_google_suggestions(seed)
        for s in suggestions:
            clean_s = s.strip().title()
            if clean_s and clean_s.lower() not in seen:
                seen.add(clean_s.lower())
                
                # Tagging logic
                tag = "🔥 Google Live Trending"
                ticket = "High Ticket"
                if "plot" in clean_s.lower() or "land" in clean_s.lower():
                    tag = "🏡 Hot Plot Query"
                    ticket = "High Ticket"
                elif "rera" in clean_s.lower():
                    tag = "🏛️ RERA Verified"
                elif "commercial" in clean_s.lower():
                    tag = "💰 Commercial Land"
                    ticket = "Enterprise"

                # City inference
                inferred_city = "Patna"
                if "ranchi" in clean_s.lower():
                    inferred_city = "Ranchi"
                elif "jamshedpur" in clean_s.lower():
                    inferred_city = "Jamshedpur"
                elif "dhanbad" in clean_s.lower():
                    inferred_city = "Dhanbad"
                elif "muzaffarpur" in clean_s.lower():
                    inferred_city = "Muzaffarpur"
                elif "bihta" in clean_s.lower():
                    inferred_city = "Patna"

                synced_items.append({
                    "keyword": clean_s,
                    "tag": tag,
                    "ticket": ticket,
                    "source": "google",
                    "cities": [inferred_city]
                })
        time.sleep(0.1)  # polite throttle

    cache_data = {
        "date": today_str,
        "last_sync": datetime.now().strftime("%I:%M %p, %d %b %Y"),
        "count": len(synced_items),
        "keywords": synced_items
    }
    _MEM_CACHE = cache_data

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return cache_data

def get_google_sync_status():
    """Return status of daily Google sync."""
    global _MEM_CACHE
    if _MEM_CACHE and _MEM_CACHE.get("keywords"):
        return {
            "synced": True,
            "date": _MEM_CACHE.get("date"),
            "last_sync": _MEM_CACHE.get("last_sync"),
            "count": _MEM_CACHE.get("count", 0)
        }
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                _MEM_CACHE = cached
                return {
                    "synced": True,
                    "date": cached.get("date"),
                    "last_sync": cached.get("last_sync"),
                    "count": cached.get("count", 0)
                }
        except Exception:
            pass
    return {
        "synced": False,
        "date": None,
        "last_sync": "Not synced yet",
        "count": 0
    }

def get_categories():
    """Return business categories and sub-categories."""
    categories_list = []
    for cat in BUSINESS_CATEGORIES:
        categories_list.append({
            "id": cat["id"],
            "name": cat["name"],
            "icon": cat["icon"],
            "color": cat["color"],
            "featured": cat.get("featured", False),
            "description": cat.get("description", ""),
            "sub_categories": [
                {"id": sub["id"], "name": sub["name"], "icon": sub["icon"], "count": len(sub["keywords"])}
                for sub in cat["sub_categories"]
            ]
        })
    return categories_list

def get_regions():
    """Return region hierarchy for Bihar and Jharkhand."""
    return REGIONS

def recommend_keywords(state="all", category="all", sub_category="all", query="", city="", limit=24):
    """
    Intelligent recommendation engine with category & subcategory support,
    daily Google live keywords integration, and balanced distribution across ALL business niches.
    """
    state_norm = (state or "all").lower()
    category_norm = (category or "all").lower()
    sub_category_norm = (sub_category or "all").lower()
    query_norm = (query or "").lower().strip()
    city_norm = (city or "").lower().strip()

    target_cities_bihar = [c["name"] for c in REGIONS["bihar"]["cities"]]
    target_cities_jharkhand = [c["name"] for c in REGIONS["jharkhand"]["cities"]]
    
    if state_norm == "bihar":
        allowed_cities = set(target_cities_bihar)
    elif state_norm == "jharkhand":
        allowed_cities = set(target_cities_jharkhand)
    else:
        allowed_cities = set(target_cities_bihar + target_cities_jharkhand)

    if city_norm:
        matching_cities = [c for c in allowed_cities if city_norm in c.lower()]
        if matching_cities:
            allowed_cities = set(matching_cities)

    # If category == "all" and no query is searched:
    # Build a rich, balanced catalog taking top keywords across ALL 11 business categories
    if category_norm == "all" and not query_norm and sub_category_norm == "all":
        category_buckets = {}
        for cat in BUSINESS_CATEGORIES:
            category_buckets[cat["id"]] = []
            for sub in cat["sub_categories"]:
                for item in sub["keywords"]:
                    applicable_cities = [c for c in item.get("cities", []) if c in allowed_cities]
                    if not applicable_cities:
                        applicable_cities = list(allowed_cities)
                    rec_city = random.choice(applicable_cities) if applicable_cities else "Patna"
                    c_state = "Bihar" if rec_city in target_cities_bihar else "Jharkhand"
                    c_flag = "🟢" if c_state == "Bihar" else "🟠"

                    category_buckets[cat["id"]].append({
                        "keyword": item["keyword"],
                        "category_id": cat["id"],
                        "category_name": cat["name"],
                        "category_icon": cat["icon"],
                        "category_color": cat["color"],
                        "sub_category_id": sub["id"],
                        "sub_category_name": sub["name"],
                        "sub_category_icon": sub["icon"],
                        "tag": item.get("tag", "🔥 High Demand"),
                        "ticket": item.get("ticket", "High Ticket"),
                        "best_source": "google",
                        "recommended_city": rec_city,
                        "state": c_state,
                        "state_flag": c_flag,
                        "relevance": random.uniform(1.0, 2.0),
                        "is_google_live": False
                    })
        
        # Take 2-3 items from EACH category to ensure broad business coverage
        interleaved = []
        for cat_id, items in category_buckets.items():
            random.shuffle(items)
            interleaved.extend(items[:2])  # 2 from each of 11 categories = 22 items

        # Add 3-4 Google Live Trending items
        try:
            google_items = get_cached_google_keywords()
            if google_items:
                g_sample = random.sample(google_items, min(4, len(google_items)))
                for g_item in g_sample:
                    applicable_cities = [c for c in g_item.get("cities", []) if c in allowed_cities]
                    if not applicable_cities:
                        applicable_cities = list(allowed_cities)
                    rec_city = random.choice(applicable_cities) if applicable_cities else "Patna"
                    c_state = "Bihar" if rec_city in target_cities_bihar else "Jharkhand"
                    c_flag = "🟢" if c_state == "Bihar" else "🟠"
                    interleaved.append({
                        "keyword": g_item["keyword"],
                        "category_id": "realestate_plots",
                        "category_name": "Real Estate & Plots",
                        "category_icon": "🏡",
                        "category_color": "#10b981",
                        "sub_category_id": "res_plots",
                        "sub_category_name": "Google Live Trending",
                        "sub_category_icon": "🔴",
                        "tag": g_item.get("tag", "🔥 Google Trending"),
                        "ticket": g_item.get("ticket", "High Ticket"),
                        "best_source": "google",
                        "recommended_city": rec_city,
                        "state": c_state,
                        "state_flag": c_flag,
                        "relevance": 1.9,
                        "is_google_live": True
                    })
        except Exception:
            pass

        random.shuffle(interleaved)
        seen = set()
        final_list = []
        for r in interleaved:
            k = (r["keyword"].lower(), r["recommended_city"].lower())
            if k not in seen:
                seen.add(k)
                final_list.append(r)
        return final_list[:limit]

    # Otherwise (filtered by category or with query search)
    recommendations = []
    for cat in BUSINESS_CATEGORIES:
        if category_norm != "all" and cat["id"] != category_norm:
            continue

        for sub in cat["sub_categories"]:
            if sub_category_norm != "all" and sub["id"] != sub_category_norm:
                continue

            for item in sub["keywords"]:
                keyword_text = item["keyword"]
                relevance = 1.0

                if query_norm:
                    if query_norm in keyword_text.lower() or query_norm in sub["name"].lower() or query_norm in cat["name"].lower():
                        relevance += 4.0
                    else:
                        tokens = re.findall(r'\w+', query_norm)
                        matched_tokens = [t for t in tokens if t in keyword_text.lower() or t in sub["name"].lower()]
                        if matched_tokens:
                            relevance += len(matched_tokens) * 1.5
                        else:
                            continue

                applicable_cities = [c for c in item.get("cities", []) if c in allowed_cities]
                if not applicable_cities:
                    applicable_cities = list(allowed_cities)

                recommended_city = random.choice(applicable_cities) if applicable_cities else "Patna"
                city_state = "Bihar" if recommended_city in target_cities_bihar else "Jharkhand"
                city_flag = "🟢" if city_state == "Bihar" else "🟠"

                recommendations.append({
                    "keyword": keyword_text,
                    "category_id": cat["id"],
                    "category_name": cat["name"],
                    "category_icon": cat["icon"],
                    "category_color": cat["color"],
                    "sub_category_id": sub["id"],
                    "sub_category_name": sub["name"],
                    "sub_category_icon": sub["icon"],
                    "tag": item.get("tag", "🔥 High Demand"),
                    "ticket": item.get("ticket", "High Ticket"),
                    "best_source": "google",
                    "recommended_city": recommended_city,
                    "state": city_state,
                    "state_flag": city_flag,
                    "relevance": relevance + random.uniform(0.1, 0.4),
                    "is_google_live": False
                })

    if category_norm in ["all", "realestate_plots"]:
        try:
            google_items = get_cached_google_keywords()
            for g_item in google_items:
                g_kw = g_item["keyword"]
                relevance = 2.0

                if query_norm:
                    if query_norm in g_kw.lower():
                        relevance += 5.0
                    else:
                        tokens = re.findall(r'\w+', query_norm)
                        matched_tokens = [t for t in tokens if t in g_kw.lower()]
                        if matched_tokens:
                            relevance += len(matched_tokens) * 1.8
                        else:
                            continue

                applicable_cities = [c for c in g_item.get("cities", []) if c in allowed_cities]
                if not applicable_cities:
                    applicable_cities = list(allowed_cities)

                rec_city = random.choice(applicable_cities) if applicable_cities else "Patna"
                c_state = "Bihar" if rec_city in target_cities_bihar else "Jharkhand"
                c_flag = "🟢" if c_state == "Bihar" else "🟠"

                recommendations.append({
                    "keyword": g_kw,
                    "category_id": "realestate_plots",
                    "category_name": "Real Estate & Plots",
                    "category_icon": "🏡",
                    "category_color": "#10b981",
                    "sub_category_id": "res_plots",
                    "sub_category_name": "Google Live Trending",
                    "sub_category_icon": "🔴",
                    "tag": g_item.get("tag", "🔥 Google Trending"),
                    "ticket": g_item.get("ticket", "High Ticket"),
                    "best_source": "google",
                    "recommended_city": rec_city,
                    "state": c_state,
                    "state_flag": c_flag,
                    "relevance": relevance + random.uniform(0.1, 0.4),
                    "is_google_live": True
                })
        except Exception:
            pass

    seen_keys = set()
    deduped = []
    for r in recommendations:
        key = (r["keyword"].lower(), r["recommended_city"].lower())
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(r)

    deduped.sort(key=lambda x: x["relevance"], reverse=True)
    return deduped[:limit]
