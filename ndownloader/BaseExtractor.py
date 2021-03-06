from bs4 import BeautifulSoup
import utils
import concurrent.futures
import requests
import urllib3
import http
import re
import os
import time
import ctypes
from fake_useragent import UserAgent
import urllib.parse
import shutil
import unicodedata

class BaseExtractor(object):
    def __init__(self, dirname=None):
        self.BASE_DIR = dirname if dirname is not None else self._create_init_directory()
        self.GALLERY_DIR_NAME = ""
        self.headers = {
            "User-Agent" : UserAgent().random,
        }
        self.links = {
            "base" : "https://nhentai.to",
            "artist" : "https://nhentai.to/artist/",
            "tag": "https://nhentai.to/tag/",
            "character" : "https://nhentai.to/character/",
            "parody": "https://nhentai.to/parody/",
            "group": "https://nhentai.to/group/",
            "random" : "https://nhentai.to/random/",
            "gallery": "https://nhentai.to/g/",
            "search" : "https://nhentai.to/search?", 
            "direct_link" : "https://t.dogehls.xyz/galleries/",
        }


    def _create_init_directory(self):
        default_dir = os.path.join(os.path.dirname(__file__), 'automated')
        if os.path.exists(default_dir) == False:
            os.mkdir(default_dir)
            print('Default directory created.')
        else:
            print('Default directory exists.')
        return default_dir
        
    
    def _create_gallery_directory(self, dirname=None):
        newdir = os.path.join(self.BASE_DIR, dirname[:260])
        if os.path.exists(newdir) == False:
            os.mkdir(newdir)
        return newdir
    
    
    def _create_temp_directory(self):
        path = os.path.join(self.BASE_DIR, "_temp")
        if os.path.exists(path) == False:
            os.mkdir(path)
            ctypes.windll.kernel32.SetFileAttributesW(path, 2)
            print("Temporary directory created.")
        else:
            print("Temporary directory already exists.")
        return path
    
    
    def _convert_directory_to_zip(self, path):
        try:
            directory_name = os.path.basename(path)[:260]
            clean_path = os.path.join(self.BASE_DIR, directory_name)
            os.remove(os.path.join(clean_path, "Thumbs.db"))
            shutil.make_archive(clean_path, "zip", os.path.join(self.BASE_DIR, self.GALLERY_DIR_NAME))
        finally:
            shutil.rmtree(x)


    ###########################################
    # Scrape images from one gallery
    ###########################################   
    def _scrape_images_from_page(self, url=None, zip_=None):
        if url is None:
            raise ValueError("'url' parameter is required.")
        _image_links = list()
        invalid_chars = f'<>:"\/|?*.@'
        pattern = r'[' + invalid_chars + ']'
        html = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(html.content, 'lxml')        
        _id = re.findall(r"/([0-9].+)", html.url)[0]            
        title = soup.find("h1").text
        containers = soup.find_all("div", "thumb-container")
        print("Title: {0}".format(title))                       
        print("ID: {0}".format(_id))
        print("Number of images: {0}".format(len(containers)))
        x = re.sub(pattern, ' ', title)
        self.GALLERY_DIR_NAME = f"{_id}-{x}"[:260]
        self._create_gallery_directory(dirname=self.GALLERY_DIR_NAME)
            
        for image in containers:
            _image_link = image.find("a", "gallerythumb").get('href')
            _full_link = self.links['base'] + _image_link
            _image_links.append(_full_link)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.get_file, _image_links)
            
        if zip_ == True:
            self._convert_directory_to_zip(path=self.GALLERY_DIR_NAME)
            
            
    ####################################
    # Scrape galleries from page
    ####################################
    def scrape_galleries_from_page(self, url=None, pages=None, per_page=None):
        if pages is not None and int(pages) > 100:
            raise ValueError("'pages' parameter must not exceed 100.") 
        while True:
            try:
                try:
                    html = requests.get(url).content
                    soup = BeautifulSoup(html, 'lxml')
                    max_pages = soup.find("a", "next").find_previous_sibling("a").text
                except AttributeError:
                    max_pages = 1
                    
                gallery__links = list()
                for page in range(1, (pages + 1)) if pages is not None else (range(1, 2)):
                    if page > int(max_pages):
                        break
                    else:
                        augmented_url = url + ("page={0}".format(page) if url[-1] == "?" else "?page={0}".format(page))
                        html = requests.get(augmented_url).content
                        soup = BeautifulSoup(html, 'lxml')
                        galleries = soup.find_all('div', 'gallery')
                        print("scraping page: {0}".format(page))
                        print("Augmented link: {0}".format(augmented_url))
                        print("Number of galleries in page: {0}".format(len(galleries)))
                        
                        for gallery in galleries[:per_page] if per_page is not None else galleries:
                            gallery_link = gallery.find("a", "cover").get("href")
                            link = self.links['base'] + gallery_link
                            gallery__links.append(link)
                        break 
                          
            except (requests.exceptions.ConnectionError, urllib3.exceptions.ConnectionError) as e:
                print("Connection aborted. Waiting for {0} second(s) and trying again.".format(3))
                time.sleep(3)
                continue
            
            return gallery__links


    def get_file(self, link):
        while True:
            print("Downloading...\n")
            try:   
                html = requests.get(link).content
                soup = BeautifulSoup(html, "lxml")
                if soup.find('title').text == "nhentai.to | 504: Gateway time-out":
                    print("Gateway Timeout Error...Retrying.")
                    time.sleep(2)
                    continue
                if soup.find('title').text == "nhentai.to | 520: Web server is returning an unknown error":
                    print("520: Server just hit a wall...Retrying in 2 second(s)")
                    time.sleep(2)
                    continue
                if soup.find("img", "fit-horizontal").get('src') != None:
                    _direct_link = soup.find("img", "fit-horizontal").get('src')
                    with requests.get(_direct_link, stream=True, timeout=5, headers=self.headers) as r:
                        r.raise_for_status()
                        _name = re.findall(r".+/([0-9].+.[a-z].+)", _direct_link)[0]
                        x = os.path.join(self.BASE_DIR, self.GALLERY_DIR_NAME)
                        with open(os.path.join(x, _name), "wb") as f:
                            for chunk in r.iter_content():
                                if chunk:
                                    f.write(chunk)                 
                break
                        
            except requests.exceptions.HTTPError:
                print('HTTP Error. Retrying...')
                time.sleep(2)
                continue
            
            except requests.exceptions.Timeout as TimeOutError:
                print('Taking too long...trying again')
                time.sleep(2)
                continue
            
            except (requests.exceptions.ConnectionError, urllib3.exceptions.ConnectionError) as e:
                print("connection aborted. waiting for {0} second(s) and trying again.".format(2))
                time.sleep(2)
                continue
        
        
    def _get_gallery(self,gallery_list=None, _title=None):
        _mdir = self._create_gallery_directory(dirname=_title)
        _direct_link = ""
        _count = 0
        try:
            for idx, link in enumerate(gallery_list):
                while True:
                    print("Downloading...")
                    try:   
                        html = requests.get(link).content
                        soup = BeautifulSoup(html, "lxml")
                        if soup.find('title').text == "nhentai.to | 504: Gateway time-out":
                            print("Gateway Timeout Error...Retrying.")
                            time.sleep(2)
                            continue
                        if soup.find('title').text == "nhentai.to | 520: Web server is returning an unknown error":
                            print("520: Server just hit a wall...Retrying in 2 second(s)")
                            time.sleep(2)
                            continue
                        if soup.find("img", "fit-horizontal").get('src') != None:
                            _direct_link = soup.find("img", "fit-horizontal").get('src')
                            with requests.get(_direct_link, stream=True, timeout=5, headers=self.headers) as r:
                                r.raise_for_status()
                                _name = re.findall(r".+/([0-9].+.[a-z].+)", _direct_link)[0]
                                with open(os.path.join(_mdir, _name), "wb") as f:
                                    for chunk in r.iter_content():
                                        if chunk:
                                            f.write(chunk)  
                        break
              
                    except requests.exceptions.HTTPError:
                        print('HTTP Error. Retrying...')
                        time.sleep(2)
                        continue
                    
                    except requests.exceptions.Timeout as TimeOutError:
                        print('Taking too long...trying again')
                        time.sleep(2)
                        continue
                    
                    except (requests.exceptions.ConnectionError, urllib3.exceptions.ConnectionError) as e:
                        print("connection aborted. waiting for {0} second(s) and trying again.".format(2))
                        time.sleep(2)
                        continue
                _count += 1
                print("Downloaded {0} out of {1}".format((idx + 1), len(gallery_list)))
                time.sleep(2)
        finally:
            print("Gallery downloaded. {0} out of {1} image(s) were saved.".format(_count, len(gallery_list)))
            print("==========================================================\n")
            time.sleep(2)



