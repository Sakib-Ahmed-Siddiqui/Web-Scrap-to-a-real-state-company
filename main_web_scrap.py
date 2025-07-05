import requests
import time
import random
import pandas as pd
import os

url = "https://api.realcommercial.com.au/listing-ui/searches?featureFlags=showSoldDisclaimer,lsapiLocations"

payload = {
    "channel": "buy",
    "localities": [
        {"locality": "canterbury bankstown", "subdivision": "nsw"},
        {"locality": "eastern suburbs", "subdivision": "nsw"},
        {"locality": "inner west", "subdivision": "nsw"},
        {"locality": "liverpool greater region", "subdivision": "nsw"},
        {"locality": "lower north shore", "subdivision": "nsw"},
        {"locality": "macarthur region", "subdivision": "nsw"},
        {"locality": "northern beaches", "subdivision": "nsw"},
        {"locality": "parramatta greater region", "subdivision": "nsw"},
        {"locality": "penrith greater region", "subdivision": "nsw"},
        {"locality": "south western sydney", "subdivision": "nsw"},
        {"locality": "st george", "subdivision": "nsw"},
        {"locality": "sutherland shire", "subdivision": "nsw"},
        {"locality": "the hills", "subdivision": "nsw"},
        {"locality": "upper north shore", "subdivision": "nsw"},
        {"locality": "western sydney", "subdivision": "nsw"},
        {"locality": "sydney cbd", "subdivision": "nsw"},
        {"locality": "sydney", "subdivision": "nsw", "postcode": "2000"}
    ],
    "filters": {
        "within-radius": "includesurrounding",
        "surrounding-suburbs": True
    },
    "sort": {
        "order": "listing-date-newest-first"
    },
    "page-size": 100
}

headers = {
    "Content-Type": "application/json"
}

output_file = "real_estate_listings.xlsx"

# Load previous data if exists
if os.path.exists(output_file):
    existing_df = pd.read_excel(output_file)
    all_data = existing_df.to_dict(orient="records")
    print(f"Loaded existing {len(all_data)} records from Excel.")
    # Since first row is header, row count = total rows - 1
    existing_count = len(existing_df)
else:
    all_data = []
    existing_count = 0
    print("No existing data found. Starting fresh.")

# Calculate starting page based on how many listings are already collected
page_size = payload["page-size"]
start_page = (existing_count // page_size) + 1
print(f"Resuming from page {start_page} (skipping {existing_count} listings already saved).")

def save_to_excel(data):
    df = pd.DataFrame(data)
    df.to_excel(output_file, index=False)

def fetch_data():
    page = start_page
    total_results = None

    while True:
        try:
            payload["page"] = page
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            if total_results is None:
                total_results = data.get("availableResults", 0)
                print(f"Total Results Found: {total_results}")

            listings = data.get("listings", [])
            if not listings:
                print("No more listings found. Exiting.")
                break

            page_data = []
            for listing in listings:
                pdp_url = listing.get("pdpUrl", "")
                page_data.append({
                    "Listing URL": pdp_url
                })

            all_data.extend(page_data)
            save_to_excel(all_data)
            print(f"Saved page {page} with {len(listings)} listings to Excel.")

            page += 1
            if (page - 1) * page_size >= total_results:
                print("All listings scraped.")
                break

            delay = random.randint(10, 15)
            print(f"Waiting {delay} seconds before fetching next page...")
            time.sleep(delay)

        except Exception as e:
            print(f"Error on page {page}: {e}")
            print("Sleeping 30 seconds before retrying...")
            time.sleep(30)
            # Do not increment page on error to retry
            continue

fetch_data()
print(f"Scraping complete. Total listings saved: {len(all_data)}")













# import requests
# import time
# import random
# import pandas as pd
# import os

# url = "https://api.realcommercial.com.au/listing-ui/searches?featureFlags=showSoldDisclaimer,lsapiLocations"

# payload = {
#     "channel": "buy",
#     "localities": [
#         {"locality": "canterbury bankstown", "subdivision": "nsw"},
#         {"locality": "eastern suburbs", "subdivision": "nsw"},
#         {"locality": "inner west", "subdivision": "nsw"},
#         {"locality": "liverpool greater region", "subdivision": "nsw"},
#         {"locality": "lower north shore", "subdivision": "nsw"},
#         {"locality": "macarthur region", "subdivision": "nsw"},
#         {"locality": "northern beaches", "subdivision": "nsw"},
#         {"locality": "parramatta greater region", "subdivision": "nsw"},
#         {"locality": "penrith greater region", "subdivision": "nsw"},
#         {"locality": "south western sydney", "subdivision": "nsw"},
#         {"locality": "st george", "subdivision": "nsw"},
#         {"locality": "sutherland shire", "subdivision": "nsw"},
#         {"locality": "the hills", "subdivision": "nsw"},
#         {"locality": "upper north shore", "subdivision": "nsw"},
#         {"locality": "western sydney", "subdivision": "nsw"},
#         {"locality": "sydney cbd", "subdivision": "nsw"},
#         {"locality": "sydney", "subdivision": "nsw", "postcode": "2000"}
#     ],
#     "filters": {
#         "within-radius": "includesurrounding",
#         "surrounding-suburbs": True
#     },
#     "sort": {
#         "order": "listing-date-newest-first"
#     },
#     "page-size": 10
# }

# headers = {
#     "Content-Type": "application/json"
# }

# output_file = "real_estate_listings.xlsx"

# # Load previous data if exists
# if os.path.exists(output_file):
#     existing_df = pd.read_excel(output_file)
#     all_data = existing_df.to_dict(orient="records")
#     print(f"Loaded existing {len(all_data)} records from Excel.")
# else:
#     all_data = []

# def save_to_excel(data):
#     df = pd.DataFrame(data)
#     df.to_excel(output_file, index=False)

# def fetch_data():
#     page = 1
#     total_results = None

#     while True:
#         try:
#             payload["page"] = page
#             response = requests.post(url, json=payload, headers=headers)
#             response.raise_for_status()

#             data = response.json()

#             if total_results is None:
#                 total_results = data.get("availableResults", 0)
#                 print(f"Total Results Found: {total_results}")

#             listings = data.get("listings", [])
#             if not listings:
#                 break

#             page_data = []
#             for listing in listings:
#                 pdp_url = listing.get("pdpUrl", "")

#                 page_data.append({
#                     "Listing URL": pdp_url
#                 })

#             all_data.extend(page_data)
#             save_to_excel(all_data)
#             print(f"Saved page {page} with {len(listings)} listings to Excel.")

#             page += 1
#             if (page - 1) * payload["page-size"] >= total_results:
#                 break

#             delay = random.randint(10, 15)
#             print(f"Waiting {delay} seconds before fetching next page...")
#             time.sleep(delay)

#         except Exception as e:
#             print(f"Error on page {page}: {e}")
#             page += 1
#             continue

# fetch_data()
# print(f"Scraping complete. Total listings saved: {len(all_data)}")
