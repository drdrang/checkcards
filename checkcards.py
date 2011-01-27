#!/usr/bin/python

import mechanize
from BeautifulSoup import BeautifulSoup
from datetime import timedelta, datetime
import re

# Card and email information. Uncomment and change this to suit your situation.
# The "code" entry in each cardList dictionary is the patron's library barcode.
# mailFrom = 'someone@example.com'
# mailTo = 'someone@example.com'
# cardList = [
# {'patron' : 'Mom', 'code' : '12345678901234', 'pin' : '1234'},
# {'patron' : 'Dad', 'code' : '98765432109876', 'pin' : '9876'},
# {'patron' : 'Kid', 'code' : '45678912345678', 'pin' : '4567'}]

# The URLs for the library's account information.
# Login
lURL = 'https://library.naperville-lib.org:443/patroninfo~S1/IIITICKET&scope=1'
# Checked-out items
cURL = 'https://library.naperville-lib.org:443/patroninfo~S1/1110947/items'
# On-hold items
hURL = 'https://library.naperville-lib.org:443/patroninfo~S1/1110947/holds'

# Initialize the lists of checked-out and on-hold items.
checkedOut = []
onHold = []

# Dates to compare with due dates. "Soon" is 2 days from today.
today = datetime.now()
soon = datetime.now() + timedelta(2)

# Function that returns an HTML table row for checked out items.
def cRow(data):
  if data[0] <= today:         # due today or overdue
    classString = ' class="due"'
  elif data[0] <= soon:        # due soon
    classString = ' class="soon"'
  else:
    classString = ''
  return '''<tr%s><td>%s</td><td>%s</td><td>%s</td></tr>''' % \
  (classString, data[0].strftime('%b %d'), data[2], data[1])

# Function that returns an HTML table row for items on hold.
def hRow(data):
  if data[0] <= 0:  # Waiting for pickup or in transit
    classString = ' class="due"'
  else:
    classString = ''
  return '''<tr%s><td>%s</td><td>%s</td><td>%s</td></tr>''' % \
  (classString, data[3], data[2], data[1])

# Go through each card, collecting the lists of items.
for card in cardList:
  # Need to use cookies to retain the session after login.
  cookies = mechanize.CookieJar()
  opener = mechanize.build_opener(mechanize.HTTPCookieProcessor(cookies))
  mechanize.install_opener(opener)
  
  # Login
  br = mechanize.Browser()
  br.set_handle_robots(False)
  br.open(lURL)
  br.select_form(nr=0)    # the login form is the first on the page
  br['code'] = card['code']
  br['pin'] = card['pin']
  resp = br.submit()
  
  # Get the pages.
  cHtml = br.open(cURL).read()
  hHtml = br.open(hURL).read()
  
  # Parse the HTML.
  cSoup = BeautifulSoup(cHtml)
  hSoup = BeautifulSoup(hHtml)

  # Collect the table rows that contain the items.
  loans = cSoup.findAll('tr', {'class' : 'patFuncEntry'})
  holds = hSoup.findAll('tr', {'class' : 'patFuncEntry'})
  
  # Due dates and pickup dates are of the form mm-dd-yy.
  itemDate = re.compile(r'\d\d-\d\d-\d\d')
  
  # Go through each row of checked out items, keeping only the title and due date.
  for item in loans:
    # The title is everything before the spaced slash in the patFuncTitle
    # string. Some titles have a patFuncVol span after the title string;
    # that gets filtered out by contents[0].
    title = item.find('td', {'class' : 'patFuncTitle'}).a.contents[0].split(' / ')[0].strip()
    
    # The due date is somewhere in the patFuncStatus cell.
    dueString = itemDate.findall(item.find('td', {'class' : 'patFuncStatus'}).contents[0])[0]
    due = datetime.strptime(dueString, '%m-%d-%y')
    # Add the item to the checked out list. Arrange tuple so items
    # get sorted by due date.
    checkedOut.append((due, card['patron'], title))
  
  # Go through each row of holds, keeping only the title and place in line.
  for item in holds:
    # Again, the title is everything before the spaced slash.
    title = item.find('td', {'class' : 'patFuncTitle'}).a.string.split(' / ')[0].strip()
    # The book's status in the hold queue will be either:
    # 1. 'n of m holds'
    # 2. 'Ready. Must be picked up by mm-dd-yy'
    # 3. 'IN TRANSIT'
    status = item.find('td', {'class' : 'patFuncStatus'}).contents[0].strip()
    n = status.split()[0]
    if n.isdigit():                         # possibility 1
      n = int(n)
      status = status.replace(' holds', '')
    elif n[:5] == 'Ready':                  # possibility 2
      n = -1
      readyString = itemDate.findall(status)[0]
      ready = datetime.strptime(readyString, '%m-%d-%y')
      status = 'Ready<br/> ' + ready.strftime('%b %d')
    else:                                   # possibility 3
      n = 0
    # Add the item to the on hold list. Arrange tuple so items
    # get sorted by position in queue. The position is faked for
    # items ready for pickup and in transit within the library. 
    onHold.append((n, card['patron'], title, status))

# Sort the lists.
checkedOut.sort()
onHold.sort()

# Templates for the email.
mailHeader = '''From: %s
To: %s
Subject: Library items
Content-Type: text/html
'''

pageHeader = '''<html>
<head>
<style type="text/css">
body {
  font-family: Helvetica, Sans-serif;
}
h1 {
  font-size: 150%%;
  margin-top: 1.5em;
  margin-bottom: .25em;
}
table {
  border-collapse: collapse; 
}
table th {
  padding: .5em 1em .25em 1em;
  background-color: #ddd;
  border: 1px solid black;
  border-bottom: 2px solid black;
}
table tr.due {
  background-color: #fcc;
}
table tr.soon {
  background-color: #ffc;
}
table td {
  padding: .25em 1em .25em 1em;
  border: 1px solid black;
}
</style>
</head>
<body>
<p>Hours: Mon-Fri: 9am - 9pm;  Sat: 9am - 5pm;  Sun: 1pm - 5pm</p>
<p>As of %s</p>
'''

tableTemplate = '''<h1>%s</h1>
<table>
<tr><th>%s</th><th>Title</th><th>Card</th></tr>
%s
</table>
'''

pageFooter = '''</body>
</html>'''

# Print out the email header and contents. This should be piped to sendmail.
print mailHeader % (mailFrom, mailTo)
print pageHeader % datetime.now().strftime('%I:%M %p on %b %d, %Y')
print (tableTemplate % ('Checked out', 'Due', '\n'.join([cRow(x) for x in checkedOut]))).encode('utf8')
print (tableTemplate % ('On hold', 'Status', '\n'.join([hRow(x) for x in onHold]))).encode('utf8')
print pageFooter
