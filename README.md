# BiddingWorks

Housingworks is a non-profit in based in NYC that fights AIDS and homelessness. They run a series of thrift shops which often have great items up for auction. I created a web scraper that will periodically notify me of the items. 

The service uses BS4 to scrape the data and then the free version of SendGrid to email me the results.
Currently, emails with items will be sent at 10 AM, 12 PM, 9 PM on days where there is an auction ending. Auctions usually end at 10 pm.
Adjust the email recipients and senders as necessary.

Requires an output and logs folder to be created in the root directory to house those files.
Create a secrets.py file that assigns `SENDGRID_API_KEY='YOUR KEY HERE'` Make sure to get the SENDGRID_API_KEY and then use the email registered as the from for API key.

Note that this doesn't do any bidding on the items.

