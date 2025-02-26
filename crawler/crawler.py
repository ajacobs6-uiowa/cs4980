from playwright.sync_api import sync_playwright, Playwright
import json
from urllib.parse import urljoin, urlparse, urlsplit
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

    # define a variable to hold the main url for each page visit
    current_main_url = None

    # ---------------------------------------------------------------------
    # 4. data structures for storing results
    # ---------------------------------------------------------------------
    all_packets = []
    packet_counter = 0
    extracted_bidding_data = []

    # ---------------------------------------------------------------------
    # 5. define a handler for capturing each network response (only xhr/fetch)
    # ---------------------------------------------------------------------
    def handle_response(response):
        nonlocal packet_counter, current_main_url
        # check if the response is xhr or fetch, else skip
        resource_type = response.request.resource_type
        if resource_type not in ["xhr", "fetch"]:
            return

        try:
            content_type = response.headers.get("content-type", "")
            status = response.status
            req_url = response.url
            website = urlparse(req_url).netloc

            # derive the packet name from the request url path
            path = urlsplit(req_url).path
            packet_name = os.path.basename(path) if path and path != "/" else "homepage"

            # try to get the payload from the response
            try:
                if ("application/json" in content_type or "text" in content_type or
                    "application/javascript" in content_type):
                    payload = response.text()
                else:
                    payload = None
            except Exception as body_error:
                print(f"error getting response payload: {body_error}")
                payload = None

            # preview: first 500 characters of payload if available
            preview = payload[:500] if payload and isinstance(payload, str) else None

            # initiator: use referer header if available
            initiator = response.request.headers.get("referer", None)

            # size: use content-length header or length of payload (if text) as fallback
            size = int(response.headers.get("content-length", 0))
            if not size and payload and isinstance(payload, str):
                size = len(payload)

            # current timestamp
            time_stamp = datetime.datetime.now().isoformat()

            # get cookies for this request url from the page context
            cookies = page.context.cookies(req_url)

            # build the packet info dictionary
            packet_info = {
                "packet_index": packet_counter,
                "name": packet_name,
                "status": status,
                "type": resource_type,
                "initiator": initiator,
                "size": size,
                "time": time_stamp,
                "headers": dict(response.headers),
                "payload": payload,
                "preview": preview,
                "response": {"url": req_url, "status": status},
                "cookies": cookies,
                "main_url": current_main_url
            }
            all_packets.append(packet_info)

            # attempt to parse payload for bidding data
            if payload:
                try:
                    parsed_json = json.loads(payload)
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
                    if "bids" in payload or "bidid" in payload or "price" in payload:
                        extracted_bidding_data.append({
                            "packet_index": packet_counter,
                            "website": website,
                            "request_url": req_url,
                            "snippet": payload[:500]
                        })
        except Exception as e:
            print(f"error handling response: {e}")

        packet_counter += 1

    # ---------------------------------------------------------------------
    # 6. attach the network response handler
    # ---------------------------------------------------------------------
    page.on("response", handle_response)

    # ---------------------------------------------------------------------
    # 7. iterate over the first 5 urls and gather network data
    # ---------------------------------------------------------------------
    for url in urls[:1]:
        current_main_url = url  # set the main url for this visit
        print(f"visiting: {url}")
        try:
            page.goto(url, timeout=120000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)  # wait 5 seconds to let ads load
        except Exception as e:
            print(f"error with the url: {url}: {e}")

    # ---------------------------------------------------------------------
    # 8. done crawling. close browser.
    # ---------------------------------------------------------------------
    browser.close()

    # ---------------------------------------------------------------------
    # 9. write out all the collected data to files
    # ---------------------------------------------------------------------
    for packet_info in all_packets:
        packet_index = packet_info["packet_index"]
        # get the main site from the main_url field
        main_url = packet_info.get("main_url", "unknown")
        main_netloc = urlparse(main_url).netloc if main_url else "unknown"
        # filename: packetX_NAME_URL.json
        file_name = f"packet{packet_index}_{packet_info['name']}_{main_netloc}.json"
        packet_path = os.path.join(raw_data_dir, file_name)
        with open(packet_path, "w", encoding="utf-8") as pf:
            json.dump(packet_info, pf, indent=4)

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
