import requests
from logging.handlers import TimedRotatingFileHandler
import logging
from logging import Formatter, getLogger
from random import randint
from bs4 import BeautifulSoup
from time import sleep
import re
from os.path import exists
from datetime import datetime, timedelta
from pytz import timezone
from shutil import copyfile
import pandas as pd
import os
from sendgrid import SendGridAPIClient, To
from sendgrid.helpers.mail import Mail
from tenacity import stop_after_delay, retry, stop_after_attempt

MAIN_URL = "https://auction.housingworks.org"
CURRENT_TIMESTAMP = datetime.now(timezone("US/Eastern"))
HOURS_TO_RUN = (9, 12, 21)

latest_csv_filename = "latest_output.csv"
latest_html_filename = "latest_output.html"


def create_logger() -> object:
    """
    this creates the logger and the subsequent management
    :return:
    """
    logger = getLogger()
    handler = TimedRotatingFileHandler(
        filename="logs/runtime.log",
        when="D",
        interval=1,
        backupCount=10,
        encoding="utf-8",
        delay=False,
    )
    formatter = Formatter(fmt=f"%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


@retry(stop=(stop_after_delay(2) | stop_after_attempt(3)))
def get_location_auctions(main_url: str) -> list:
    """
    this retrieves the list of individual housingworks locations with auctions
    :param main_url: the main url for the housingworks auction page
    :return: list of urls
    """
    auctions_page = requests.get(f"{main_url}/auctions")
    soup = BeautifulSoup(auctions_page.text, "html.parser")
    location_auction_urls = [
        f"{main_url}" + ana["href"]
        for ana in soup.findAll("a")
        if ana.parent.name == "h2"
    ]
    return location_auction_urls


@retry(stop=(stop_after_delay(2) | stop_after_attempt(3)))
def retrieve_auction_location_items(location_auction_url: str) -> list:
    """
    this retrieves the list items for auction at the specified location
    :param location_auction_url: the url for the specific location
    :rtype: list of lists that contains the location auction items
    """
    auctions_page = requests.get(location_auction_url)
    auctions_page_soup = BeautifulSoup(auctions_page.text, "html.parser")
    auction_location_items = []
    item_images = []
    for thumbnail in auctions_page_soup.findAll("div", attrs={"class": "thumb-list"}):
        item_images.append(thumbnail.find("img")["src"])
    location_name = auctions_page_soup.find("h2", attrs={"class": "page-title"}).text
    for idx, thumb in enumerate(
            auctions_page_soup.findAll("div", attrs={"class": "thumbpadding"})
    ):
        item_link = thumb.find("a")["href"]
        item_name = thumb.find("div", attrs={"class": "title"}).text
        item_current_bid = thumb.find("span").text
        item_auction_time = thumb.find(
            "div", attrs={"class": "price auctions-time"}
        ).text
        auction_location_items.append(
            [
                location_name,
                item_name,
                item_images[idx],
                item_current_bid,
                item_auction_time,
                item_link,
                CURRENT_TIMESTAMP,
            ]
        )
    return auction_location_items


def path_to_image_html(path):
    return '<img src="' + path + '" width="60" >'


def write_to_csv_html(all_auction_location_items: list):
    """
    this takes the scraped data and then exports it to a csv
    :param all_auction_location_items: list of lists for the items
    """
    header = [
        "loc_name",
        "item_name",
        "item_image",
        "item_current_bid",
        "item_auction_time",
        "item_link",
        "scraped_at_local",
    ]
    df = pd.DataFrame(all_auction_location_items, columns=header)
    df["scraped_at_local"] = pd.to_datetime(df["scraped_at_local"])
    df["auction_end_date"] = df.apply(
        lambda x: get_auction_end_date(x.item_auction_time, x.scraped_at_local), axis=1
    )
    df.sort_values("auction_end_date", inplace=True)
    df.to_csv(latest_csv_filename, index_label=False)
    df.to_html(
        latest_html_filename,
        render_links=True,
        escape=False,
        formatters={"item_image": path_to_image_html},
    )
    str_current_time = CURRENT_TIMESTAMP.strftime("%Y%m%d_%H")
    copyfile("latest_output.csv", f"./outputs/{str_current_time}_output.csv")


def get_auction_end_date(item_auction_time: str, current_time: datetime) -> datetime:
    """
    function passed through pandas lambda to take the current time and countdown to determine auction end
    :param item_auction_time: how much time is left in the auction
    :param current_time: what is the current time
    :return:
    """
    days = int(re.findall(r"(\d+)d", item_auction_time)[0])
    hours = int(re.findall(r"(\d+)h", item_auction_time)[0])
    mins = int(re.findall(r"(\d+)m", item_auction_time)[0])
    auction_end_date = current_time + timedelta(minutes=mins, hours=hours, days=days)
    return auction_end_date


def send_email(html_filename: str):
    """
    this sends the actual email off to the different recipients
    :param html_filename: this is the panads to_html output that will be the body of the email
    """
    html_file = open(html_filename, "r", encoding="utf-8").read()
    message = Mail(
        from_email="john@johnpham.me",
        to_emails=[To("john.pham.92@gmail.com")],
        subject=f"Housing Works Run {CURRENT_TIMESTAMP}",
        is_multiple=True,
        html_content=html_file,
    )
    try:
        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        response = sg.send(message)
        logging.info("Successful Email Sent")
    except Exception as e:
        logging.warning(e.message)


def check_run_program() -> bool:
    """
    this checks whether the program should execute
    :rtype: bool
    """
    if not exists("latest_output.csv"):
        logging.info("First run")
        return True
    df = pd.read_csv("latest_output.csv")
    df["auction_end_date"] = pd.to_datetime(df["auction_end_date"])
    for auction_end_date in df["auction_end_date"].unique():
        if (
                auction_end_date.strftime("%m/%d/%Y")
                == CURRENT_TIMESTAMP.strftime("%m/%d/%Y")
        ) and (CURRENT_TIMESTAMP.hour in HOURS_TO_RUN):
            logging.info("Date of auction end timed run")
            return True


def main():
    create_logger()
    if not check_run_program():
        return
    location_auction_urls = get_location_auctions(MAIN_URL)
    all_auction_location_items = []
    for location_auction_url in location_auction_urls:
        sleep(randint(0, 2))
        all_auction_location_items.extend(
            retrieve_auction_location_items(location_auction_url)
        )
        logging.info(f"completed {location_auction_url}")
    write_to_csv_html(all_auction_location_items)
    send_email(latest_html_filename)
    logging.info(f"completed run")


if __name__ == "__main__":
    main()
