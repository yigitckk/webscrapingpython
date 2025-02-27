from bs4 import BeautifulSoup
import requests

# Fetch the page content
html_text = requests.get('https://weworkremotely.com').text
# Parse the HTML content
soup = BeautifulSoup(html_text, 'lxml')
jobs = soup.find_all('li', class_='new-listing-container feature pro')
for job in jobs:
    company_name = job.find('p', class_ = 'new-listing__company-name').text.replace(' ','')
    type = job.find('div', class_='new-listing__categories').text.replace(' ',',')
    published_date = job.find('span', class_ = 'new')
    print(type)
    print(company_name)

    print(' ')
