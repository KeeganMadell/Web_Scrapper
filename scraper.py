from bs4 import BeautifulSoup
import requests

url = ""

response = requests.get(url)

print(response)