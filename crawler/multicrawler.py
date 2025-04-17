import sys
import asyncio
from playwright.async_api import async_playwright, Playwright, WebError
import json
from urllib.parse import urljoin, urlparse, urlsplit
import os
import datetime

async def run(playwright: Playwright):
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
    # 3. Create the browser through Playwright
    # ---------------------------------------------------------------------
    
    chromium = playwright.chromium
    
    browser = await chromium.launch(headless=False)



    #----------------------------------------------------------------------
    # 4. Setting async collection of the data files
    #----------------------------------------------------------------------
    work_queue = asyncio.Queue()
    persona_list = {"low-income.txt", "first-gen.txt", "lgbtq+.txt", "hispanic-latino.txt", "physical-disability.txt", "refugee.txt", "veteran.txt", "women-in-stem.txt", "youtube-preteen.txt"}
    #persona_list = {"empty.txt"}
    for persona in persona_list:
        await work_queue.put(persona)

    
    await asyncio.gather(
        asyncio.create_task(persona_task("One",base_dir, bidding_dir,browser, urls, work_queue)),
        asyncio.create_task(persona_task("Two", base_dir, bidding_dir,browser, urls, work_queue)),
        asyncio.create_task(persona_task("Three",base_dir, bidding_dir,browser, urls, work_queue)),
        asyncio.create_task(persona_task("Four",base_dir, bidding_dir,browser, urls, work_queue)),
        asyncio.create_task(persona_task("Five", base_dir, bidding_dir,browser, urls, work_queue)),
        )
    await browser.close()

    



async def persona_task(number, base_dir, bidding_dir, browser, urls, work_queue):
    print(number + " beginning to work")
    while not work_queue.empty():
        persona_list = await work_queue.get()
        with open(os.path.join(base_dir, persona_list), "r") as file:
            url_list = [line.strip() for line in file if line.strip()]    

        task_window =  await browser.new_context()

        page =  await task_window.new_page()


        for url in url_list:
            print(number + f" visiting {url}")
            try:
                await page.goto(url, wait_until="load", timeout=0)
                await page.wait_for_timeout(700)
            
            except Exception as e:
                print(f"Error with the url: {url} : {e}")
                await page.wait_for_timeout(10000)

        #---------------------------------------------
        # Collect the CPM data
        #---------------------------------------------
        bid_data = []
        for url in urls:
            try:
                await page.goto(url, wait_until="load", timeout=0)  # wait 5 seconds to let ads load
                await page.wait_for_timeout(5000)
                collected_data = await page.evaluate("window.pbjs.getAllPrebidWinningBids()")
                if(collected_data != None):
                    for item in collected_data:
                        value = item["cpm"]
                        bid_data.append(value)

            except TypeError as e:
            # try again
                await page.wait_for_timeout(5000)
                collected_data = await page.evaluate("window.pbjs.getAllPrebidWinningBids()")
                if(collected_data != None):
                    for item in collected_data:
                        value = item["cpm"]
                        bid_data.append(value)

            except Exception as e:
                print(f"Error with the url: {url} : {e}")
                await page.wait_for_timeout(10000)


        #---------------------------------------------
        # Done crawling, get it all done.
        #---------------------------------------------
        await task_window.close()

        bidding_data_path = os.path.join(bidding_dir, f"bidding_data_{work_queue}.json")
        with open(bidding_data_path, "w", encoding="utf-8") as bf:
            json.dump(bid_data, bf, indent=4)

        print(number + " has finished collecting data!")


async def main():
    async with async_playwright() as playwright:
        await run(playwright)
asyncio.run(main())