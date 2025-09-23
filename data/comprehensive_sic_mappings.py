# Comprehensive SIC Code Mappings for SectorClassificationAgent
# Based on official UK SIC 2007 classification system
# Generated from SIC_codes.xlsx with intelligent keyword extraction

COMPREHENSIVE_SIC_MAPPINGS = {
    # Agriculture, Forestry and Fishing (1xxx-3xxx)
    "01110": {
        "description": "Growing of cereals (except rice), leguminous crops and oil seeds",
        "keywords": ["farming", "agriculture", "cereals", "crops", "growing", "grain"]
    },
    "01410": {
        "description": "Raising of dairy cattle", 
        "keywords": ["dairy", "cattle", "milk", "farming", "livestock"]
    },
    "02100": {
        "description": "Silviculture and other forestry activities",
        "keywords": ["forestry", "timber", "trees", "silviculture"]
    },
    "03110": {
        "description": "Marine fishing",
        "keywords": ["fishing", "marine", "seafood", "commercial"]
    },
    
    # Energy and Utilities (35xx-39xx)
    "35110": {
        "description": "Production of electricity",
        "keywords": ["electricity", "power", "energy", "generation"]
    },
    "36000": {
        "description": "Water collection, treatment and supply",
        "keywords": ["water", "treatment", "supply", "utility"]
    },
    "38110": {
        "description": "Collection of non-hazardous waste",
        "keywords": ["waste", "collection", "recycling", "environmental"]
    },
    
    # Construction (41xx-43xx)
    "41200": {
        "description": "Construction of residential and non-residential buildings",
        "keywords": ["construction", "building", "residential", "commercial"]
    },
    "42110": {
        "description": "Construction of roads and motorways", 
        "keywords": ["construction", "roads", "infrastructure", "civil"]
    },
    "43210": {
        "description": "Electrical installation",
        "keywords": ["electrical", "installation", "construction", "wiring"]
    },
    
    # Retail and Wholesale (45xx-47xx)
    "45110": {
        "description": "Sale of cars and light motor vehicles",
        "keywords": ["cars", "vehicles", "automotive", "sales", "dealer"]
    },
    "46310": {
        "description": "Wholesale of fruit and vegetables",
        "keywords": ["wholesale", "fruit", "vegetables", "produce", "fresh"]
    },
    "46510": {
        "description": "Wholesale of computers, computer peripheral equipment and software",
        "keywords": ["wholesale", "computers", "technology", "software", "IT"]
    },
    "47110": {
        "description": "Retail sale in non-specialised stores with food, beverages or tobacco predominating",
        "keywords": ["retail", "supermarket", "grocery", "food", "general"]
    },
    "47190": {
        "description": "Other retail sale in non-specialised stores",
        "keywords": ["retail", "department", "general", "variety"]
    },
    "47210": {
        "description": "Retail sale of fruit and vegetables in specialised stores",
        "keywords": ["retail", "fruit", "vegetables", "fresh", "produce"]
    },
    "47410": {
        "description": "Retail sale of computers, peripheral units and software in specialised stores",
        "keywords": ["retail", "computers", "technology", "electronics", "software"]
    },
    "47710": {
        "description": "Retail sale of clothing in specialised stores",
        "keywords": ["retail", "clothing", "fashion", "apparel", "garments"]
    },
    "47730": {
        "description": "Dispensing chemist in specialised stores",
        "keywords": ["pharmacy", "chemist", "medicine", "healthcare", "drugs"]
    },
    "47910": {
        "description": "Retail sale via mail order houses or via Internet",
        "keywords": ["retail", "online", "internet", "ecommerce", "mail order"]
    },
    
    # Transportation (49xx-53xx)
    "49100": {
        "description": "Passenger rail transport, interurban",
        "keywords": ["rail", "passenger", "transport", "railway", "train"]
    },
    "49410": {
        "description": "Freight transport by road",
        "keywords": ["freight", "road", "transport", "trucking", "logistics"]
    },
    "50200": {
        "description": "Sea and coastal freight water transport",
        "keywords": ["shipping", "freight", "marine", "cargo", "transport"]
    },
    "51100": {
        "description": "Passenger air transport",
        "keywords": ["airline", "passenger", "aviation", "air", "transport"]
    },
    "52100": {
        "description": "Warehousing and storage",
        "keywords": ["warehousing", "storage", "logistics", "distribution"]
    },
    "53200": {
        "description": "Other postal and courier activities",
        "keywords": ["courier", "delivery", "express", "logistics"]
    },
    
    # Hospitality (55xx-56xx) - KEY FOR COMPASS GROUP
    "55100": {
        "description": "Hotels and similar accommodation",
        "keywords": ["hotel", "accommodation", "hospitality", "lodging", "guest"]
    },
    "56101": {
        "description": "Licenced restaurants", 
        "keywords": ["restaurant", "dining", "food", "licensed", "alcohol", "catering"]
    },
    "56102": {
        "description": "Unlicenced restaurants and cafes",
        "keywords": ["restaurant", "cafe", "food", "dining", "unlicensed", "catering"]
    },
    "56210": {
        "description": "Event catering activities",
        "keywords": ["catering", "events", "food", "service", "hospitality"]
    },
    "56290": {
        "description": "Other food service activities",
        "keywords": ["food", "service", "catering", "mobile", "hospitality"]
    },
    "56303": {
        "description": "Public houses and bars",
        "keywords": ["pub", "bar", "alcohol", "drinks", "hospitality"]
    },
    
    # Information and Communication (58xx-63xx)
    "58210": {
        "description": "Publishing of computer games",
        "keywords": ["gaming", "software", "entertainment", "technology"]
    },
    "59110": {
        "description": "Motion picture, video and television programme production activities",
        "keywords": ["film", "video", "television", "production", "media"]
    },
    "60100": {
        "description": "Radio broadcasting",
        "keywords": ["radio", "broadcasting", "media", "transmission"]
    },
    "60200": {
        "description": "Television programming and broadcasting activities",
        "keywords": ["television", "broadcasting", "media", "programming"]
    },
    "61100": {
        "description": "Wired telecommunications activities",
        "keywords": ["telecommunications", "wired", "internet", "broadband"]
    },
    "61200": {
        "description": "Wireless telecommunications activities",
        "keywords": ["mobile", "wireless", "telecommunications", "cellular"]
    },
    "62010": {
        "description": "Computer programming activities",
        "keywords": ["programming", "software", "development", "coding", "IT"]
    },
    "62020": {
        "description": "Computer consultancy activities",
        "keywords": ["consulting", "IT", "technology", "advice", "systems"]
    },
    "63110": {
        "description": "Data processing, hosting and related activities",
        "keywords": ["data", "hosting", "processing", "cloud", "IT"]
    },
    "63120": {
        "description": "Web portals",
        "keywords": ["web", "portal", "internet", "online", "digital"]
    },
    
    # Financial Services (64xx-66xx) - KEY FOR HSBC
    "64110": {
        "description": "Central banking",
        "keywords": ["central", "bank", "banking", "monetary", "financial"]
    },
    "64191": {
        "description": "Banks",
        "keywords": ["bank", "banking", "financial", "services", "lending", "deposit"]
    },
    "64192": {
        "description": "Building societies",
        "keywords": ["building", "society", "mortgage", "savings", "financial"]
    },
    "64301": {
        "description": "Activities of investment trusts",
        "keywords": ["investment", "trust", "financial", "fund"]
    },
    "64910": {
        "description": "Financial leasing",
        "keywords": ["leasing", "financial", "rental", "equipment"]
    },
    "64920": {
        "description": "Other credit granting",
        "keywords": ["credit", "lending", "finance", "loans"]
    },
    "65110": {
        "description": "Life insurance",
        "keywords": ["insurance", "life", "assurance", "coverage"]
    },
    "65120": {
        "description": "Non-life insurance",
        "keywords": ["insurance", "general", "coverage", "protection"]
    },
    "66120": {
        "description": "Security and commodity contracts brokerage",
        "keywords": ["brokerage", "securities", "trading", "investment"]
    },
    
    # Real Estate (68xx)
    "68100": {
        "description": "Buying and selling of own real estate",
        "keywords": ["real estate", "property", "buying", "selling", "development"]
    },
    "68200": {
        "description": "Renting and operating of own or leased real estate",
        "keywords": ["rental", "property", "leasing", "real estate", "landlord"]
    },
    "68310": {
        "description": "Real estate agencies",
        "keywords": ["estate", "agent", "property", "real estate", "sales"]
    },
    
    # Professional Services (69xx-75xx)
    "69101": {
        "description": "Barristers at law",
        "keywords": ["legal", "barrister", "law", "advocate", "court"]
    },
    "69102": {
        "description": "Solicitors",
        "keywords": ["legal", "solicitor", "law", "attorney", "advice"]
    },
    "69201": {
        "description": "Accounting and auditing activities",
        "keywords": ["accounting", "audit", "financial", "bookkeeping", "tax"]
    },
    "70220": {
        "description": "Business and other management consultancy activities",
        "keywords": ["consulting", "management", "business", "advisory", "strategy"]
    },
    "71111": {
        "description": "Architectural activities",
        "keywords": ["architecture", "design", "building", "construction", "planning"]
    },
    "71122": {
        "description": "Engineering related scientific and technical consulting activities",
        "keywords": ["engineering", "consulting", "technical", "scientific", "advice"]
    },
    "72110": {
        "description": "Research and experimental development on biotechnology",
        "keywords": ["research", "biotechnology", "development", "scientific", "R&D"]
    },
    "73110": {
        "description": "Advertising agencies",
        "keywords": ["advertising", "agency", "marketing", "promotion", "creative"]
    },
    "73200": {
        "description": "Market research and public opinion polling",
        "keywords": ["market research", "polling", "survey", "analysis", "data"]
    },
    "74200": {
        "description": "Photographic activities",
        "keywords": ["photography", "photo", "imaging", "visual", "commercial"]
    },
    "75000": {
        "description": "Veterinary activities",
        "keywords": ["veterinary", "animal", "health", "medical", "care"]
    },
    
    # Manufacturing (selected key codes)
    "10110": {
        "description": "Processing and preserving of meat",
        "keywords": ["food", "meat", "processing", "manufacturing"]
    },
    "11010": {
        "description": "Distilling, rectifying and blending of spirits",
        "keywords": ["spirits", "alcohol", "distilling", "beverages"]
    },
    "20110": {
        "description": "Manufacture of industrial gases", 
        "keywords": ["chemicals", "gases", "industrial", "manufacturing"]
    },
    "26110": {
        "description": "Manufacture of electronic components",
        "keywords": ["electronics", "components", "technology", "manufacturing"]
    },
    "27110": {
        "description": "Manufacture of electric motors, generators and transformers",
        "keywords": ["electrical", "motors", "generators", "manufacturing"]
    },
    "28110": {
        "description": "Manufacture of engines and turbines, except aircraft, vehicle and cycle engines",
        "keywords": ["engines", "turbines", "machinery", "manufacturing"]
    },
    "30300": {
        "description": "Manufacture of air and spacecraft and related machinery",
        "keywords": ["aircraft", "aerospace", "aviation", "manufacturing", "aerospace engineering"]
    },
    
    # Education and Healthcare
    "85100": {
        "description": "Pre-primary education",
        "keywords": ["education", "pre-primary", "nursery", "early years"]
    },
    "85200": {
        "description": "Primary education",
        "keywords": ["education", "primary", "school", "teaching"]
    },
    "85310": {
        "description": "General secondary education",
        "keywords": ["education", "secondary", "school", "teaching"]
    },
    "85421": {
        "description": "First-degree level higher education",
        "keywords": ["university", "education", "degree", "higher education"]
    },
    "86101": {
        "description": "Hospital activities",
        "keywords": ["hospital", "medical", "healthcare", "treatment"]
    },
    "86210": {
        "description": "General medical practice activities",
        "keywords": ["medical", "GP", "healthcare", "practice", "doctor"]
    },
    "86220": {
        "description": "Specialist medical practice activities",
        "keywords": ["medical", "specialist", "healthcare", "consultant"]
    },
    
    # Entertainment and Recreation
    "90010": {
        "description": "Performing arts",
        "keywords": ["performing", "arts", "theatre", "entertainment", "culture"]
    },
    "91020": {
        "description": "Museum activities",
        "keywords": ["museum", "cultural", "heritage", "exhibition"]
    },
    "93110": {
        "description": "Operation of sports facilities",
        "keywords": ["sports", "facilities", "recreation", "fitness", "leisure"]
    },
    "93210": {
        "description": "Activities of amusement parks and theme parks",
        "keywords": ["amusement", "theme park", "entertainment", "leisure"]
    }
}