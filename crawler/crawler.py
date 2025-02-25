from playwright.sync_api import sync_playwright, Playwright
import json
from urllib.parse import urljoin, urlparse
import os
import datetime

def run(playwright: Playwright):
    # ---------------------------------------------------------------------
    # 1. prepare output directories for this run
    # ---------------------------------------------------------------------
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.dirname(os.path.realpath(__file__))  # path to this script
    data_storage_dir = os.path.join(base_dir, "data_storage")
    run_dir = os.path.join(data_storage_dir, f"run_{timestamp}")
    raw_data_dir = os.path.join(run_dir, "raw_data")
    bidding_dir = os.path.join(run_dir, "bidding_data")

    # make sure directories exist
    os.makedirs(raw_data_dir, exist_ok=True)
    os.makedirs(bidding_dir, exist_ok=True)

    # ---------------------------------------------------------------------
    # 2. read in the list of urls
    # ---------------------------------------------------------------------
    with open(os.path.join(base_dir, "urls.txt"), "r") as file:
        urls = [line.strip() for line in file if line.strip()]

    # ---------------------------------------------------------------------
    # 3. launch browser (chromium)
    # ---------------------------------------------------------------------
    chrome = playwright.chromium
    browser = chrome.launch(headless=False)
    page = browser.new_page()

    # ---------------------------------------------------------------------
    # 4. data structures for storing results
    # ---------------------------------------------------------------------
    # store all response data (for raw saving)
    # we'll collect them in memory, then write them to files
    # key: incrementing integer for packet index
    # value: a dict with relevant info (url, status, headers, body, etc.)
    all_packets = []
    packet_counter = 0

    # bidding data we extract from responses
    # we'll store them in a list and then write to bidding_data.json
    extracted_bidding_data = []

    # ---------------------------------------------------------------------
    # 5. define a handler for capturing each network response (only xhr/fetch)
    # ---------------------------------------------------------------------
    def handle_response(response):
        nonlocal packet_counter

        # check if the response is xhr or fetch, else skip
        resource_type = response.request.resource_type
        if resource_type not in ["xhr", "fetch"]:
            return

        try:
            # some responses may fail to return text (e.g., binary). we handle that:
            content_type = response.headers.get("content-type", "")
            status = response.status
            req_url = response.url
            website = urlparse(req_url).netloc

            # decide whether to get text or binary
            if "application/json" in content_type or "text" in content_type or "application/javascript" in content_type:
                body = response.text()  # safer for text-based content
            else:
                # if it's binary or unknown, store as none
                body = None

            packet_info = {
                "packet_index": packet_counter,
                "website": website,
                "request_url": req_url,
                "status": status,
                "headers": dict(response.headers),
                "body": body
            }
            all_packets.append(packet_info)

            # -----------------------------------------------------------------
            # 5a. attempt to parse body for bidding data
            # -----------------------------------------------------------------
            if body:
                # try json first
                try:
                    parsed_json = json.loads(body)

                    # heuristic check for "bids" or "price" fields
                    if "bids" in parsed_json:
                        extracted_bidding_data.append({
                            "packet_index": packet_counter,
                            "website": website,
                            "request_url": req_url,
                            "bids": parsed_json["bids"]
                        })
                    elif "price" in parsed_json:
                        extracted_bidding_data.append({
                            "packet_index": packet_counter,
                            "website": website,
                            "request_url": req_url,
                            "price": parsed_json["price"]
                        })
                except json.JSONDecodeError:
                    # if it's not valid json, check for keywords in the text
                    if "bids" in body or "bidid" in body or "price" in body:
                        extracted_bidding_data.append({
                            "packet_index": packet_counter,
                            "website": website,
                            "request_url": req_url,
                            "snippet": body[:500]  # store a snippet to see if it's relevant
                        })
        except Exception as e:
            # if anything goes wrong capturing a response, just log
            print(f"error handling response: {e}")

        # increment for next packet
        packet_counter += 1

    # ---------------------------------------------------------------------
    # 6. attach the network response handler
    #    we do this before visiting each url so we catch all traffic
    # ---------------------------------------------------------------------
    page.on("response", handle_response)

    # ---------------------------------------------------------------------
    # 7. iterate over each url and gather network data
    # ---------------------------------------------------------------------

    # for url in urls:
    #     print(f"visiting: {url}")
    #     try:
    #         page.goto(url, timeout=120000)
    #         page.wait_for_load_state("networkidle")  # ensure we capture most traffic
    #         # wait briefly on the homepage to let ads load
    #         page.wait_for_timeout(5000)  # wait for 5 seconds
    #     except Exception as e:
    #         print(f"error with the url: {url}: {e}")

    for url in urls[:5]:
        print(f"visiting: {url}")
        try:
            page.goto(url, timeout=120000)
            page.wait_for_load_state("networkidle")  # ensure we capture most traffic
            # wait briefly on the homepage to let ads load
            page.wait_for_timeout(5000)  # wait for 5 seconds
        except Exception as e:
            print(f"error with the url: {url}: {e}")

    # ---------------------------------------------------------------------
    # 8. done crawling. close browser.
    # ---------------------------------------------------------------------
    browser.close()

    # ---------------------------------------------------------------------
    # 9. write out all the collected data to files
    # ---------------------------------------------------------------------
    # 9a. write raw packets: each packet in a separate file
    for packet_info in all_packets:
        packet_index = packet_info["packet_index"]
        packet_path = os.path.join(raw_data_dir, f"packet_{packet_index}.json")
        with open(packet_path, "w", encoding="utf-8") as pf:
            json.dump(packet_info, pf, indent=4)

    # 9b. write bidding data
    bidding_data_path = os.path.join(bidding_dir, "bidding_data.json")
    with open(bidding_data_path, "w", encoding="utf-8") as bf:
        json.dump(extracted_bidding_data, bf, indent=4)

    print("crawler has finished collecting data!")

# -------------------------------------------------------------------------
# 10. entry point: run with sync_playwright
# -------------------------------------------------------------------------
if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
