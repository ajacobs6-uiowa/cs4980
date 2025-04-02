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
    #all_packets = []
    #packet_counter = 0
    #extracted_bidding_data = []
    bid_data = []
    bid_counter = 0
    


    #----------------------------------------------------------
    # Getting the results of winning bids
    #----------------------------------------------------------
    def getWinningBids():
        return page.add_script_tag(path='analyzeBid.js')
    

    # ---------------------------------------------------------------------
    # 7. iterate over the urls and gather network data
    # ---------------------------------------------------------------------
    for url in urls:
        current_main_url = url  # set the main url for this visit
        print(f"visiting: {url}")
        try:
            page.goto(url, timeout=120000)
            #page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)  # wait 5 seconds to let ads load
            collected_data = page.evaluate("window.pbjs.getAllPrebidWinningBids")
            if(collected_data != None):
                for item in collected_data:
                    value = item["cpm"]
                    print(value)
                    bid_data.append(value)
        
        except Exception as e:
            print(f"error with the url: {url}: {e}")

    # ---------------------------------------------------------------------
    # 8. done crawling. close browser.
    # ---------------------------------------------------------------------
    browser.close()

    # ---------------------------------------------------------------------
    # 9. write out all the collected data to files
    # ---------------------------------------------------------------------
    cpm_values = []
    for bid_info in bid_data:
        cpm_values.append(bid_info)

    print(cpm_values)
    

    print("crawler has finished collecting data!")
    
    '''for packet_info in all_packets:
        packet_index = packet_info["packet_index"]
        # get the main site from the main_url field
        main_url = packet_info.get("main_url", "unknown")
        main_netloc = urlparse(main_url).netloc if main_url else "unknown"
        #filename: packetX_NAME_URL.json
        file_name = f"packet{packet_index}_{packet_info['name']}_{main_netloc}.json"
        packet_path = os.path.join(raw_data_dir, file_name)
        with open(packet_path, "w", encoding="utf-8") as pf:
            json.dump(packet_info, pf, indent=4)

    bidding_data_path = os.path.join(bidding_dir, "bidding_data.json")
    with open(bidding_data_path, "w", encoding="utf-8") as bf:
        json.dump(extracted_bidding_data, bf, indent=4)

    print("crawler has finished collecting data!")
    '''
# -------------------------------------------------------------------------
# 10. entry point: run with sync_playwright
# -------------------------------------------------------------------------
if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright) 