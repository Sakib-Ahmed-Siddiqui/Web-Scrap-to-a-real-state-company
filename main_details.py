import pandas as pd
import requests
import time
import re
import os
from datetime import datetime, timedelta

INPUT_FILE = "real_estate_listings.xlsx"
OUTPUT_FILE = "detailed_listings.xlsx"

ZONING_MAP = {
    "Neighbourhood Centre": "B1",
    "Local Centre": "B2",
    "Commercial Core": "B3",
    "Mixed Use": "B4",
    "Business Development": "B5",
    "Enterprise Corridor": "B6",
    "Business Park": "B7",
    "Metropolitan Centre": "B8",
    "National Parks and Nature Reserves": "E1",
    "Environmental Conservation": "E2",
    "Environmental Management": "E3",
    "Environmental Living": "E4",
    "General Industrial": "IN1",
    "Light Industrial": "IN2",
    "Heavy Industrial": "IN3",
    "Working Waterfront": "IN4",
    "General Residential": "R1",
    "Low Density Residential": "R2",
    "Medium Density Residential": "R3",
    "High Density Residential": "R4",
    "Large Lot Residential": "R5",
    "Public Recreation": "RE1",
    "Private Recreation": "RE2",
    "Primary Production": "RU1",
    "Rural Landscape": "RU2",
    "Forestry": "RU3",
    "Primary Production Small Lots": "RU4",
    "Village": "RU5",
    "Transition": "RU6",
    "Special Activities": "SP1",
    "Infrastructure": "SP2",
    "Tourist": "SP3",
    "Natural Waterways": "W1",
    "Recreational Waterways": "W2",
    "Working Waterways": "W3"
}

def extract_zoning_shortcode(zoning_raw):
    zoning_raw_lower = zoning_raw.lower()
    for long_name, code in ZONING_MAP.items():
        if long_name.lower() in zoning_raw_lower:
            return code
    # fallback regex if backend sends standard "MU1", "B2" etc
    zoning_match = re.search(r"\b([A-Z]{1,3}\d{0,2})\b", zoning_raw)
    return zoning_match.group(1) if zoning_match else zoning_raw




# Load input
df_input = pd.read_excel(INPUT_FILE)
if 'Listing URL' not in df_input.columns:
    raise Exception("Missing 'Listing URL' column in Excel file")

def extract_listing_id(url):
    match = re.search(r'(\d+)$', str(url))
    return match.group(1) if match else None

df_input['Listing ID'] = df_input['Listing URL'].apply(extract_listing_id)
df_input = df_input[df_input['Listing ID'].notnull()].reset_index(drop=True)

# Load existing output (if exists)
if os.path.exists(OUTPUT_FILE):
    df_output = pd.read_excel(OUTPUT_FILE)
    processed_ids = set()
    for url in df_input['Listing URL']:
        lid = extract_listing_id(url)
        if lid and lid in df_output.to_string():
            processed_ids.add(lid)
else:
    df_output = pd.DataFrame()
    processed_ids = set()

# API call to fetch details
def fetch_details(listing_id):
    try:
        url = f"https://api.realcommercial.com.au/listing-ui/listings/{listing_id}?channel=for-sale&featureFlags=showSoldDisclaimer,lsapiLocations"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        d = res.json().get("listing", {})

        addr = d.get("address", {})
        agencies = d.get("agencies", [])
        ag = agencies[0] if agencies else {}
        sales = ag.get("salespeople", [])

        title       = d.get("title", "")
        description = d.get("description", "")
        price_obj   = d.get("price", {}).get("forSale", {})
        price       = price_obj.get("display", "")

        # Get status: sold or on market
        # status = "On Market" if d.get("status", "").lower() != "sold" else "Sold"
        status = "Sold" if "sold" in [ch.lower() for ch in d.get("availableChannels", [])] else "On Market"
        # asking_price = price if status == "On Market" else ""
        if status == "On Market" and "$" in price:
            asking_price = price
        else:
            asking_price = ""


        # if status == "On Market" and price.strip().startswith("$"):
        #     asking_price = price
        # else:
        #     asking_price = ""


        days_active = d.get("daysActive", 0)
        date_added = (datetime.now() - timedelta(days=days_active)).strftime("%Y-%m-%d")

        attr = {a["id"]: a["value"] for a in d.get("attributes", [])}
        land_size_raw = attr.get("land-area", "")
        floor_area_raw = attr.get("floor-area", "")

        # Remove m² and spaces
        land_size = re.sub(r"[^\d.]", "", land_size_raw)
        floor_area = re.sub(r"[^\d.]", "", floor_area_raw)

        zoning_raw = attr.get("zoning", "")
        zoning = extract_zoning_shortcode(zoning_raw)

        # zoning_raw = attr.get("zoning", "")
        # zoning_match = re.search(r"\b([A-Z]{1,3}\d{0,2})\b", zoning_raw)
        # zoning = zoning_match.group(1) if zoning_match else zoning_raw



        # zoning_raw = attr.get("zoning", "")
        # # Extract zoning abbreviation from text, e.g., "Mixed Use – MU1" => "MU1"
        # zoning_match = re.search(r"([A-Z]{1,3}\d+)", zoning_raw)
        # zoning = zoning_match.group(1) if zoning_match else zoning_raw

        tenure = attr.get("tenure-type", "")

        suburb_address = addr.get("suburbAddress", "")
        # Extract postcode as numbers only (e.g., 'NSW 2127' -> '2127')
        if "," in suburb_address:
            suburb_suffix = suburb_address.split(",")[-1].strip()
            postcode_match = re.search(r"\b(\d{4})\b", suburb_suffix)
            suburb_suffix = postcode_match.group(1) if postcode_match else ""
        else:
            suburb_suffix = ""
        # suburb_suffix = suburb_address.split(",")[-1].strip() if "," in suburb_address else ""

        return {
            "Listing URL": "https://www.realcommercial.com.au" + d.get("canonicalPath", ""),
            "Street name": addr.get("streetAddress", ""),
            "Suburb": addr.get("suburb", ""),
            "Postcode": suburb_suffix,
            "Property Types": " • ".join(d.get("propertyTypes", [])),
            "Status": status,
            "Asking Price": asking_price,
            # "Price": price,
            "Land size": land_size,
            "Floor area": floor_area,
            "Zoning": zoning,
            "Tenure": tenure,
            "Date Added": date_added,
            "Agency": ag.get("name", ""),

            "Agent name 1": sales[0]["name"] if len(sales) > 0 else "",
            "Agent name 2": sales[1]["name"] if len(sales) > 1 else "",

            # "Agent name 1": (
            #     f'{sales[0]["name"]}, {sales[0]["phone"]["display"]}'
            #     if len(sales) > 0 and "phone" in sales[0] else (
            #         sales[0]["name"] if len(sales) > 0 else ""
            #     )
            # ),
            # "Agent name 2": (
            #     f'{sales[1]["name"]}, {sales[1]["phone"]["display"]}'
            #     if len(sales) > 1 and "phone" in sales[1] else (
            #         sales[1]["name"] if len(sales) > 1 else ""
            #     )
            # ),
            "Description": description
        }

    except Exception as e:
        print(f"❌ Error fetching {listing_id}: {e}")
        return {k: "" for k in [
            "Listing URL","Street name","Suburb","Postcode","Property Types",
            "Status","Asking Price","Price","Land size","Floor area","Zoning",
            "Tenure","Date Added","Agency","Agent name 1","Agent name 2","Description"
        ]}

# Loop and write after each
for idx, row in df_input.iterrows():
    listing_id = str(row["Listing ID"])
    if listing_id in processed_ids:
        print(f"⏭️ Skipping already processed ID {listing_id}")
        continue

    print(f"[{idx+1}/{len(df_input)}] Processing {listing_id}")
    details = fetch_details(listing_id)
    clean = row.drop(labels=["Listing URL","Listing ID"])
    combined = {**clean.to_dict(), **details}

    df_output = pd.concat([df_output, pd.DataFrame([combined])], ignore_index=True)
    try:
        df_output.to_excel(OUTPUT_FILE, index=False)
        print(f"✅ Saved: {listing_id}")
        processed_ids.add(listing_id)
    except Exception as write_err:
        print(f"⚠️ Failed to write after {listing_id}: {write_err}")

    time.sleep(5)














# import pandas as pd
# import requests
# import time
# import re
# import os
# from datetime import datetime

# INPUT_FILE = "real_estate_listings.xlsx"
# OUTPUT_FILE = "detailed_listings.xlsx"

# # Load input
# df_input = pd.read_excel(INPUT_FILE)
# if 'Listing URL' not in df_input.columns:
#     raise Exception("Missing 'Listing URL' column in Excel file")

# def extract_listing_id(url):
#     match = re.search(r'(\d+)$', str(url))
#     return match.group(1) if match else None

# df_input['Listing ID'] = df_input['Listing URL'].apply(extract_listing_id)
# df_input = df_input[df_input['Listing ID'].notnull()].reset_index(drop=True)

# # Load existing output (if exists)
# if os.path.exists(OUTPUT_FILE):
#     df_output = pd.read_excel(OUTPUT_FILE)
#     processed_ids = set()
#     for url in df_input['Listing URL']:
#         lid = extract_listing_id(url)
#         if lid and lid in df_output.to_string():
#             processed_ids.add(lid)
# else:
#     df_output = pd.DataFrame()
#     processed_ids = set()

# # API call to fetch details
# def fetch_details(listing_id):
#     try:
#         url = f"https://api.realcommercial.com.au/listing-ui/listings/{listing_id}?channel=for-sale&featureFlags=showSoldDisclaimer,lsapiLocations"
#         res = requests.get(url, timeout=10)
#         res.raise_for_status()
#         d = res.json().get("listing", {})

#         addr = d.get("address", {})
#         agencies = d.get("agencies", [])
#         ag = agencies[0] if agencies else {}
#         sales = ag.get("salespeople", [])

#         title       = d.get("title", "")
#         description = d.get("description", "")
#         price       = d.get("price", {}).get("forSale", {}).get("display", "")
#         # tenure      = d.get("omniture", {}).get("tenureType", "")
#         days_active = d.get("daysActive", 0)
#         added_today = "Yes" if days_active <= 7 else "No"
#         last_updated = (datetime.now() - pd.Timedelta(days=days_active)).strftime("%Y-%m-%d")

#         attr = {a["id"]: a["value"] for a in d.get("attributes", [])}
#         land_size    = attr.get("land-area", "")
#         floor_area   = attr.get("floor-area", "")
#         zoning       = attr.get("zoning", "")
#         tenure       = attr.get("tenure-type", "")

#         suburb_address = addr.get("suburbAddress", "")
#         suburb_suffix = suburb_address.split(",")[-1].strip() if "," in suburb_address else ""

#         return {
#             "Listing URL": "https://www.realcommercial.com.au" + d.get("canonicalPath", ""),
#             "Street name": addr.get("streetAddress", ""),
#             "Suburb": addr.get("suburb", ""),
#             # "SuburbAddress": suburb_address,
#             "Postcode": suburb_suffix,
#             # "Postcode": addr.get("postcode", ""),
#             "Property Types": " • ".join(d.get("propertyTypes", [])),
#             "Price": price,
#             "Land size": land_size,
#             "Floor area": floor_area,
#             "Zoning": zoning,
#             "Tenure": tenure,
#             "Added Today": added_today,
#             # "Last Updated": last_updated,
#             "Agency": ag.get("name", ""),
#                         "Agent name 1": (
#                 f'{sales[0]["name"]}, {sales[0]["phone"]["display"]}'
#                 if len(sales) > 0 and "phone" in sales[0] else (
#                     sales[0]["name"] if len(sales) > 0 else ""
#                 )
#             ),
#             "Agent name 2": (
#                 f'{sales[1]["name"]}, {sales[1]["phone"]["display"]}'
#                 if len(sales) > 1 and "phone" in sales[1] else (
#                     sales[1]["name"] if len(sales) > 1 else ""
#                 )
#             ),

#             # "Agent name 1": sales[0]["name"] if len(sales) > 0 else "",
#             # "Agent name 2": sales[1]["name"] if len(sales) > 1 else "",
#             "Description": description
#         }

#     except Exception as e:
#         print(f"❌ Error fetching {listing_id}: {e}")
#         return {k: "" for k in [
#             "Listing URL","Street name","Suburb","Postcode","Property Types",
#             "Price","Land size","Floor area","Zoning","Tenure",
#             "Added Today","Last Updated","Agency","Agent name 1","Agent name 2","Description"
#         ]}

# # Loop and write after each
# for idx, row in df_input.iterrows():
#     listing_id = str(row["Listing ID"])
#     if listing_id in processed_ids:
#         print(f"⏭️ Skipping already processed ID {listing_id}")
#         continue

#     print(f"[{idx+1}/{len(df_input)}] Processing {listing_id}")
#     details = fetch_details(listing_id)
#     clean = row.drop(labels=["Listing URL","Listing ID"])
#     combined = {**clean.to_dict(), **details}

#     df_output = pd.concat([df_output, pd.DataFrame([combined])], ignore_index=True)
#     try:
#         df_output.to_excel(OUTPUT_FILE, index=False)
#         print(f"✅ Saved: {listing_id}")
#         processed_ids.add(listing_id)
#     except Exception as write_err:
#         print(f"⚠️ Failed to write after {listing_id}: {write_err}")

#     time.sleep(5)














# import pandas as pd
# import requests
# import time
# import re
# import os

# INPUT_FILE = "real_estate_listings.xlsx"
# OUTPUT_FILE = "detailed_listings.xlsx"

# # Load input
# df_input = pd.read_excel(INPUT_FILE)

# # Ensure 'Listing URL' exists
# if 'Listing URL' not in df_input.columns:
#     raise Exception("Missing 'Listing URL' column in Excel file")

# # Extract listing ID from URL
# def extract_listing_id(url):
#     match = re.search(r'(\d+)$', str(url))
#     return match.group(1) if match else None

# df_input['Listing ID'] = df_input['Listing URL'].apply(extract_listing_id)
# df_input = df_input[df_input['Listing ID'].notnull()].reset_index(drop=True)

# # Load existing output (if exists)
# if os.path.exists(OUTPUT_FILE):
#     df_output = pd.read_excel(OUTPUT_FILE)
#     processed_ids = set()

#     # Extract processed IDs again
#     for url in df_input['Listing URL']:
#         listing_id = extract_listing_id(url)
#         if listing_id in df_output.to_string():
#             processed_ids.add(listing_id)
# else:
#     df_output = pd.DataFrame()
#     processed_ids = set()

# # API call to fetch details
# def fetch_details(listing_id):
#     try:
#         url = f"https://api.realcommercial.com.au/listing-ui/listings/{listing_id}?channel=for-sale&featureFlags=showSoldDisclaimer,lsapiLocations"
#         res = requests.get(url, timeout=10)
#         res.raise_for_status()
#         data = res.json().get("listing", {})

#         title = data.get("title", "")
#         description = data.get("description", "")
#         price = data.get("price", {}).get("forSale", {}).get("display", "")

#         attr_dict = {attr["id"]: attr["value"] for attr in data.get("attributes", [])}
#         area = attr_dict.get("floor-area", "")
#         car_spaces = attr_dict.get("car-spaces", "")
#         zoning = attr_dict.get("zoning", "")
#         municipality = attr_dict.get("municipality", "")

#         return {
#             "Title": title,
#             "Description": description,
#             "Price": price,
#             "Area": area,
#             "Car Spaces": car_spaces,
#             "Zoning": zoning,
#             "Municipality": municipality
#         }

#     except Exception as e:
#         print(f"❌ Error fetching {listing_id}: {e}")
#         return {
#             "Title": "",
#             "Description": "",
#             "Price": "",
#             "Area": "",
#             "Car Spaces": "",
#             "Zoning": "",
#             "Municipality": ""
#         }

# # Loop and write after each
# for idx, row in df_input.iterrows():
#     listing_id = str(row["Listing ID"])
#     if listing_id in processed_ids:
#         print(f"⏭️ Skipping already processed ID {listing_id}")
#         continue

#     print(f"[{idx+1}/{len(df_input)}] Processing {listing_id}")
#     data = fetch_details(listing_id)

#     # Drop Listing URL and Listing ID from input
#     clean_row = row.drop(labels=["Listing URL", "Listing ID"])
#     combined = {**clean_row.to_dict(), **data}

#     df_output = pd.concat([df_output, pd.DataFrame([combined])], ignore_index=True)

#     # Save after each entry
#     try:
#         df_output.to_excel(OUTPUT_FILE, index=False)
#         print(f"✅ Saved: {listing_id}")
#     except Exception as write_err:
#         print(f"⚠️ Failed to write after {listing_id}: {write_err}")

#     time.sleep(5)  # Gentle delay
