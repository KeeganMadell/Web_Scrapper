from bs4 import BeautifulSoup
import requests
from urllib import *
from urllib.parse import urljoin

# Stores visted urls, removing duplicates
visited_urls = set()

def spider_urls(url, keyword):
    # Tries to get a response/request from the selectd url
    try:
        response = requests.get(url)
        # if no response/request it will bringup the error bellow
    except:
        print(f"Request failed. With url: {url}")

    # Checks if the response code from url is 200(connected).
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        # if the response is 200 it will search the page for ancor tags and the hrefs in the ancor tags
        a_tag = soup.find_all('a')

        urls = [] # empty url list to append to
        
        for tag in a_tag:
            href = tag.get("href")
            if href is not None and href != "":
                urls.append(href)
        print(urls)

        # Checks if the url is not in the visted urls and if not it appends it to the 'visited_urls' set
        for i in url:
            if i not in visited_urls:
                visited_urls.add(url)
                url_join = urljoin(url, url) # creates a absolute url. urls with 'https://' not just eg, Wikipedia.com 
                if keyword in url_join:
                    print(url_join) # if the keyword is in the url it prints it and uses recursion to update the perameters(same keyword & new url)
                    spider_urls(url_join, keyword)
            else:
                pass

def main():
    # asks the user to enter a url and keyword they want to scrape
    url = input("Enter url: ")
    keyword = input("Enter keyword to search in url: ")
    # juicy results
    print(spider_urls(url, keyword))

if __name__ == '__main__':
    main()
