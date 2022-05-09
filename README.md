# BiddingWorks

Housingworks is a non-profit in based in NYC that fights AIDS and homelessness. They run a series of thrift shops which often have great items up for thrifting.
I created a web scraper that will periodically notify me of the items. 

The service uses BS4 to scrape the data and then the free version of SendGrid to email me the results. It currently runs at 8 am, 12 pm, 8 pm on the day when an auction is about to complete.
Currently, emails with items will be sent at 10 AM, 12 PM, 9 PM on days where there is an auction ending.
Adjust the email recipients and senders as necessary. APIKEY must be registered with Sendgrid for this to work along with a env variable.

Requires an output and logs folder to be created in the root directory to house those files.
Use this to set the environment variable for sendgrid: 
https://github.com/sendgrid/sendgrid-python#setup-environment-variables

Note that this doesn't do any bidding on the items.

