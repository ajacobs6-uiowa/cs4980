from playwright.sync_api import sync_playwright, Playwright
import json  
from urllib.parse import urljoin
import os

def run(playwright: Playwright):
    #get urls
    with open("urls.txt", "r") as file:
        urls = file.readlines()
    for line in urls:
        line = line.strip()
    
    chrome = playwright.chromium 
    browser = chrome.launch(headless=True)
    page = browser.new_page()
    results = []
    
    for url in urls:
        print(f"[bold green] Going to : {url}[/bold green]")
        try: 
            page.goto(url, timeout=120000)
            privacyPolicy = None
            dnsmpi = None
            dns_page_text = None
            privacy_page_text = None
            
            links = page.locator("a").element_handles()
            for link in links:
                try:
                    href = link.get_attribute("href")
                    text = link.inner_text()
                    if text: 
                        text = text.lower().strip()
                    else:
                        text = ""
                
                    if not href or href.startswith('#'):
                        print(f"Empty{href}")
                        continue
                
                    href = urljoin(url, href)
                    #print(f"Link {href} | Text: {text}")
                
                    if "privacy" in text:
                        privacyPolicy = href
                        print(f"[bold red]  Privacy Policy: [/bold red]{href}")
                        page.goto(href, timeout=60000)
                        page.wait_for_load_state("load")
                        privacy_page_text = page.inner_text("body")

                    if "Do not sell my information" in text or "do not sell my information" in text or "do not sell my info" in text or "do not sell my personal info" in text or "do not sell or share my personal information" in text:
                        dnsmpi = href
                        print(f"[bold yellow]DNSMPI link: [/bold yellow]{href}")
                        page.goto(href, timeout=60000)
                        page.wait_for_load_state("load")
                        dns_page_text = page.inner_text("body")
                except Exception as linkError:
                    print(f"[bold bright_red] Error with link:{linkError}[/bold bright_red]")
            results.append({
                "url": url,
                "Privacy Policy": privacyPolicy,
                "Do not sell my information": dnsmpi,
                "Privacy Policy Text": privacy_page_text,
                "DNSMPI": dns_page_text
            })
        except Exception as e:
            print(f"[bold bright_red] Error with the url: {url}: [/bold bright_red]{e}")

    browser.close()
    path = os.path.realpath(__file__)
    this_dir = os.path.dirname(path)
    dir = this_dir.replace("crawler", "data")
    os.chdir(dir)
    with open("scraped_privacyData.json", "w") as file:
        json.dump(results, file, indent=4)
    os.chdir(this_dir)
    print("Crawler has finished!")

with sync_playwright() as playwright:
    run(playwright)
