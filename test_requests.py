import requests
from bs4 import BeautifulSoup
import re

def fetch_ds_from_portal_requests(ds_code):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    })
    
    # 1. Login Page GET
    login_url = 'https://asclepiuswellness.com/login.aspx?webid=1'
    r = session.get(login_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value'] if soup.find('input', {'name': '__VIEWSTATE'}) else ''
    viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'] if soup.find('input', {'name': '__VIEWSTATEGENERATOR'}) else ''
    eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value'] if soup.find('input', {'name': '__EVENTVALIDATION'}) else ''
    
    # 2. Login POST
    login_data = {}
    for inp in soup.find_all('input'):
        name = inp.get('name')
        if name:
            login_data[name] = inp.get('value', '')
    
    login_data['txtspUserid'] = 'AAZFD8117G'
    login_data['txtsppassword'] = 'ABC@1234'
    login_data['btnfranlogin'] = 'Submit'
    # Remove the other submit buttons if they exist
    login_data.pop('btnsubmituser', None)
    login_data.pop('ctl00$ContentPlaceHolder1$btncustlogin', None)
    
    r2 = session.post(login_url, data=login_data)
    soup2 = BeautifulSoup(r2.text, 'html.parser')
    print("Post-login title:", soup2.title.text if soup2.title else 'No title')
    
    # 3. Sale Order Page GET
    sale_url = 'https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx'
    r3 = session.get(sale_url)
    soup3 = BeautifulSoup(r3.text, 'html.parser')
    
    viewstate3 = soup3.find('input', {'name': '__VIEWSTATE'})['value'] if soup3.find('input', {'name': '__VIEWSTATE'}) else ''
    viewstategenerator3 = soup3.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'] if soup3.find('input', {'name': '__VIEWSTATEGENERATOR'}) else ''
    eventvalidation3 = soup3.find('input', {'name': '__EVENTVALIDATION'})['value'] if soup3.find('input', {'name': '__EVENTVALIDATION'}) else ''
    
    # 4. Type DS code (Simulate text changed postback)
    # Usually ASP.NET requires __EVENTTARGET to be the ID of the textbox if AutoPostBack is true.
    # We will pass 'ctl00$ContentPlaceHolder1$txtid' as EVENTTARGET.
    sale_data = {
        '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$txtid',
        '__EVENTARGUMENT': '',
        '__LASTFOCUS': '',
        '__VIEWSTATE': viewstate3,
        '__VIEWSTATEGENERATOR': viewstategenerator3,
        '__EVENTVALIDATION': eventvalidation3,
        'ctl00$ContentPlaceHolder1$txtid': ds_code,
        # other fields might be required, ASP.NET usually sends all form inputs
    }
    
    # Add hidden fields or other inputs if necessary
    for input_tag in soup3.find_all('input'):
        name = input_tag.get('name')
        if name and name not in sale_data and input_tag.get('type') not in ['submit', 'button']:
            sale_data[name] = input_tag.get('value', '')
            
    r4 = session.post(sale_url, data=sale_data)
    soup4 = BeautifulSoup(r4.text, 'html.parser')
    
    name = soup4.find('input', {'name': 'ctl00$ContentPlaceHolder1$txtname'})
    
    if not name or not name.get('value'):
        # Let's print the title or something to see if we logged in
        print("Login failed or no name found. Title:", soup4.title.text if soup4.title else 'No title')
        print("Error message:", soup4.find(id='ctl00_ContentPlaceHolder1_lblmsg').text if soup4.find(id='ctl00_ContentPlaceHolder1_lblmsg') else 'No err msg')
        return None
    name = name['value']
        
    mobile = soup4.find('input', {'name': 'ctl00$ContentPlaceHolder1$txtmobile'})
    mobile = mobile['value'] if mobile else ''
    
    address = soup4.find('textarea', {'name': 'ctl00$ContentPlaceHolder1$txtaddress'})
    address = address.text if address else ''
    
    ship_address = soup4.find('textarea', {'name': 'ctl00$ContentPlaceHolder1$txtshipaddress'})
    ship_address = ship_address.text if ship_address else ''
    
    ship_mobile = soup4.find('input', {'name': 'ctl00$ContentPlaceHolder1$ShipMobile'})
    ship_mobile = ship_mobile['value'] if ship_mobile else ''
    
    ship_pincode = soup4.find('input', {'name': 'ctl00$ContentPlaceHolder1$txtshpingpincode'})
    ship_pincode = ship_pincode['value'] if ship_pincode else ''
    
    return {
        'ds_code': ds_code,
        'ds_name': name,
        'mobile': mobile,
        'address': address,
        'shipping_address': ship_address,
        'shipping_mobile': ship_mobile,
        'shipping_pincode': ship_pincode,
        'last_invoice': ''
    }

print(fetch_ds_from_portal_requests('B8DB3D'))
