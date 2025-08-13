import os
import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from colorama import init, Fore
from tqdm import tqdm
import threading

# ===== Init Colorama =====
init(autoreset=True)

# ===== Config =====
visited_urls = set()
lock = threading.Lock()
max_depth = 2  # recursive depth
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/114.0.0.0 Safari/537.36"}
log_file = "clone_log.txt"

# ===== Helper Functions =====
def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)

def safe_filename(url):
    parsed = urlparse(url)
    name = parsed.path.strip("/").replace("/", "_")
    if not name or name.endswith(".html"):
        name = name or "index"
    if not name.endswith(".html"):
        name += ".html"
    return name

def download_file(url, folder):
    try:
        local_name = os.path.join(folder, os.path.basename(urlparse(url).path))
        if not local_name or local_name.endswith("/"):
            return
        r = requests.get(url, headers=headers, timeout=10, stream=True)
        if r.status_code == 200:
            total = int(r.headers.get('content-length', 0))
            with open(local_name, "wb") as f, tqdm(total=total, unit='B', unit_scale=True, desc=os.path.basename(local_name), leave=False) as bar:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
                    bar.update(len(chunk))
            print(Fore.GREEN + f"[SUCCESS] {local_name}")
            log(f"[SUCCESS] {url} -> {local_name}")
    except Exception as e:
        print(Fore.RED + f"[FAILED] {url} -> {e}")
        log(f"[FAILED] {url} -> {e}")

def download_assets(soup, base_url, folder):
    asset_types = {
        "css": {"tag": "link", "attr": "href", "rel": "stylesheet"},
        "js": {"tag": "script", "attr": "src"},
        "images": {"tag": "img", "attr": "src"},
        "videos": {"tag": "video", "attr": "src"},
        "fonts": {"tag": "link", "attr": "href", "pattern": r".*\.(woff2?|ttf|otf)"},
    }
    for folder_name, cfg in asset_types.items():
        create_folder(os.path.join(folder, folder_name))
        tags = soup.find_all(cfg["tag"])
        for t in tags:
            url_attr = t.get(cfg["attr"])
            if not url_attr:
                continue
            if "rel" in cfg and t.get("rel") != [cfg["rel"]]:
                continue
            if "pattern" in cfg and not re.match(cfg["pattern"], url_attr, re.I):
                continue
            full_url = urljoin(base_url, url_attr)
            download_file(full_url, os.path.join(folder, folder_name))

def clone_page(url, folder, depth=0):
    global visited_urls
    with lock:
        if url in visited_urls or depth > max_depth:
            return
        visited_urls.add(url)

    try:
        # Selenium Headless Browser
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        html = driver.page_source
        create_folder(folder)
        filename = os.path.join(folder, safe_filename(url))
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(Fore.CYAN + f"[HTML] Saved: {filename}")
        log(f"[HTML] {url} -> {filename}")
        soup = BeautifulSoup(html, "html.parser")
        download_assets(soup, url, folder)

        # Recursive crawl internal links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("mailto:") or href.startswith("tel:"):
                continue
            full_url = urljoin(url, href)
            if urlparse(full_url).netloc == urlparse(url).netloc:
                subfolder = os.path.join(folder, href.replace("https://", "").replace("http://", "").replace("/", "_"))
                threading.Thread(target=clone_page, args=(full_url, subfolder, depth+1)).start()
        driver.quit()
    except Exception as e:
        print(Fore.RED + f"[FAILED] Cloning {url}: {e}")
        log(f"[FAILED] {url} -> {e}")

# ===== Main =====
if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    banner = """
██████╗ ██╗      ██████╗ ██╗   ██╗███╗   ██╗███████╗
██╔══██╗██║     ██╔═══██╗██║   ██║████╗  ██║██╔════╝
██████╔╝██║     ██║   ██║██║   ██║██╔██╗ ██║█████╗  
██╔═══╝ ██║     ██║   ██║██║   ██║██║╚██╗██║██╔══╝  
██║     ███████╗╚██████╔╝╚██████╔╝██║ ╚████║███████╗
╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝
        Advanced Full Site Cloner by mahdi
"""
    print(Fore.MAGENTA + banner)
    start_url = input(Fore.YELLOW + "Enter website URL (with https://): ").strip()
    folder = input(Fore.YELLOW + "Enter folder to save (default: cloned_site): ").strip()
    if not folder:
        folder = "cloned_site"
    depth_input = input(Fore.YELLOW + f"Enter recursive depth (default: 2): ").strip()
    if depth_input.isdigit():
        max_depth = int(depth_input)
    clone_page(start_url, folder)
    print(Fore.GREEN + f"[+] Cloning started. Check folder: {folder}")
