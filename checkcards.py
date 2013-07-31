#!/usr/bin/python

import mechanize
from BeautifulSoup import BeautifulSoup
from datetime import timedelta, datetime
import re
from checkcards_personal import mailFrom, mailTo, cardList

# Keep 'checkcards_personal.py' in the same directory as this
# script. It should contain library card and email information
# like the following:
# mailFrom = 'someone@example.com'
# mailTo = 'someone@example.com'
# cardList = [
# {'patron' : 'Mom', 'code' : '12345678901234', 'pin' : '1234'},
# {'patron' : 'Dad', 'code' : '98765432109876', 'pin' : '9876'},
# {'patron' : 'Kid', 'code' : '45678912345678', 'pin' : '4567'}]

# The login URL for the library's account information.
lURL = 'https://library.naperville-lib.org/iii/cas/login?service=https%3A%2F%2Flibrary.naperville-lib.org%3A443%2Fpatroninfo~S1%2FIIITICKET&scope=1'

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
  if data[0] < 0:     # Waiting for pickup
    classString = ' class="due"'
  elif data[0] == 0:  # In transit
    classString = ' class="due"'
  else:
    classString = ''
  return '''<tr%s><td>%s</td><td>%s</td><td>%s</td></tr>''' % \
  (classString, data[3], data[2], data[1])

# Go through each card, collecting the lists of items.
for card in cardList:
  # Open a browser and login
  br = mechanize.Browser()
  br.set_handle_robots(False)
  br.open(lURL)
  br.select_form(nr=0)
  br.form['code'] = card['code']
  br.form['pin'] = card['pin']
  br.submit()

  # We're now on either the page for checked-out items or for holds.
  # Get the URL and figure out which page we're on.
  pURL = br.response().geturl()
  if pURL[-5:] == 'items':                            # checked-out items
    cHtml = br.response().read()                        # get the HTML
    br.follow_link(text_regex='requests? \(holds?\)')   # go to holds
    hHtml = br.response().read()                        # get the HTML
  elif pURL[-5:] == 'holds':                          # holds
    hHtml = hHtml = br.response().read()                # get the HTML
    br.follow_link(text_regex='currently checked out')  # go to checked-out
    cHtml = br.response().read()                        # get the HTML
  else:
    continue

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
    # that gets filtered out by contents[0]. Interlibrary loans
    # don't appear as links, so there's no <a></a> inside the patFuncTitle
    # item.
    title = item.find('td', {'class' : 'patFuncTitle'}).text

    # The due date is somewhere in the patFuncStatus cell.
    dueString = itemDate.findall(item.find('td', {'class' : 'patFuncStatus'}).contents[0])[0]
    due = datetime.strptime(dueString, '%m-%d-%y')
    # Add the item to the checked out list. Arrange tuple so items
    # get sorted by due date.
    checkedOut.append((due, card['patron'], title))

  # Go through each row of holds, keeping only the title and place in line.
  for item in holds:
    # Again, the title is everything before the spaced slash. Interlibrary loans
    # are holds that don't appear as links, so there's no <a></a> inside the
    # patFuncTitle item.
    title = item.find('td', {'class' : 'patFuncTitle'}).text

    # The book's status in the hold queue will be either:
    # 1. 'n of m holds'
    # 2. 'Ready. Must be picked up by mm-dd-yy' (obsolete?)
    # 3. 'DUE mm-dd-yy'
    # 4. 'IN TRANSIT'
    status = item.find('td', {'class' : 'patFuncStatus'}).contents[0].strip()
    n = status.split()[0]
    if n.isdigit():                         # possibility 1
      n = int(n)
      status = status.replace(' holds', '')
    elif n[:5].lower() == 'ready' or n[:3].lower() == 'due':  # possibilities 2 & 3
      n = -1
      readyString = itemDate.findall(status)[0]
      ready = datetime.strptime(readyString, '%m-%d-%y')
      status = 'Ready<br/> ' + ready.strftime('%b %d')
    else:                                   # possibility 4
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
