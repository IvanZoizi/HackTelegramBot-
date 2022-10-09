import requests
from bs4 import BeautifulSoup

url = 'https://funkydubna.ru/'
response = requests.get(url)
soup = BeautifulSoup(response.text, 'lxml')
quotes = soup.find_all('h3', class_='title')

for quote in quotes:
    print(quote.text)

prices = soup.find_all('p', class_='cost')

for price in prices:
    print(price.text)

with open('fak.txt', 'r', encoding='utf-8') as file:
    text = [i.rstrip('\n') for i in file.readlines()]
print(text)
lis = []
for i in range(len(text)):
    print(prices[i].text.split('\n')[-1])
    print(prices[i].text.rstrip('\n').rstrip('\t'))
    price = prices[0].text.split('\n')[1].strip()[:-1]
    lis.append(f'{text[i]}-{price}')
    text[i] = f'{text[i]}-{prices[i].text}'
print(prices[0].text.split('\n')[1].strip()[:-1])
print(text)
print('\n'.join(lis))