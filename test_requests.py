import requests
from bs4 import BeautifulSoup
import re

def test_login_and_fetch():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # 1. GET login page
    print("GET login.aspx")
    r = session.get('https://asclepiuswellness.com/login.aspx?webid=1')
    soup = BeautifulSoup(r.text, 'html.parser')
    
    viewstate = soup.find('input', id='__VIEWSTATE')['value']
    eventvalidation = soup.find('input', id='__EVENTVALIDATION')['value']
    viewstategenerator = soup.find('input', id='__VIEWSTATEGENERATOR')['value']
    
    # 2. POST login
    print("POST login.aspx")
    login_data = {
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': viewstategenerator,
        '__EVENTVALIDATION': eventvalidation,
        'ctl00$ContentPlaceHolder1$txtspUserid': 'AAZFD8117G',
        'ctl00$ContentPlaceHolder1$txtsppassword': 'ABC@1234',
        'ctl00$ContentPlaceHolder1$btnfranlogin': 'Login'
    }
    r = session.post('https://asclepiuswellness.com/login.aspx?webid=1', data=login_data)
    
    # 3. GET FranchiseorderN.aspx
    print("GET FranchiseorderN.aspx")
    r = session.get('https://asclepiuswellness.com/shoppingpoint/FranchiseorderN.aspx')
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Let's try to simulate selecting a product (e.g., ID 55)
    viewstate = soup.find('input', id='__VIEWSTATE')['value']
    eventvalidation = soup.find('input', id='__EVENTVALIDATION')['value']
    viewstategenerator = soup.find('input', id='__VIEWSTATEGENERATOR')['value']
    
    print("POST FranchiseorderN.aspx with product 55")
    # ASP.NET auto-postback usually uses __EVENTTARGET
    postback_data = {
        '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$itemlist',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': viewstategenerator,
        '__EVENTVALIDATION': eventvalidation,
        'ctl00$ContentPlaceHolder1$itemlist': '55'
    }
    r = session.post('https://asclepiuswellness.com/shoppingpoint/FranchiseorderN.aspx', data=postback_data)
    
    soup2 = BeautifulSoup(r.text, 'html.parser')
    # Let's find inputs that might have Rate or Box size
    # Typically, Rate might be in txtrate, txtamount, txtbox, etc.
    res = {}
    for inp in soup2.find_all('input'):
        name = inp.get('name', '')
        val = inp.get('value', '')
        if 'rate' in name.lower() or 'price' in name.lower() or 'box' in name.lower() or 'qty' in name.lower() or 'pack' in name.lower():
            print(name, "=", val)

if __name__ == '__main__':
    test_login_and_fetch()
