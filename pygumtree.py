#!/usr/bin/env python3

import sys
import re
import os.path
import time
import sqlite3
import requests
from bs4 import BeautifulSoup
import smtplib

config_path = os.path.expanduser("~") + "/.config/pygumtree/"
db_name = config_path + "/gumtree.db"


def main():
    create_db(db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    query = str(sys.argv[1:])
    base_url = str("http://www.gumtree.com.au/")
    url = base_url + query + "/k0?fromSearchBox=true"
    r = requests.get(url)
    soup = BeautifulSoup(r.content)

    email, password, waiting_time = get_config()

    message = ""
    old_ad = 0
    new_ad = 0
    found = 0
    for links in soup.find_all("a"):
        link = (links.get("href"))
        ad_link = (re.search(r"/s-ad/.*", link))

        if ad_link:
            # print(match.group())
            print("ad: ")
            found = 1
            parts = ad_link.group().split("/")
            ad_id = parts[5]
            location = parts[2]
            name = parts[4]
            url = str(base_url + link)
            url = (re.sub(r"//s", "/s", url))

            # Get ad image by going into each ad's page
            individual_r = requests.get(url)
            individual_soup = BeautifulSoup(individual_r.content)
            for img_link in individual_soup.find_all("img"):
                print(img_link)

            try:
                c.execute("INSERT INTO Items VALUES(?,?,?,?);",
                          (ad_id, location, name, url))
                message += create_message(ad_id, location, name, url)
                new_ad += 1
            except sqlite3.IntegrityError:
                old_ad += 1

            conn.commit()

    print(message)
    if found == 0:
        print("No ad found.")
    if new_ad == 1:
        print("Found %d new ad. Sending email" % new_ad)
        mail(message)
        print("Will wait for an hour before searching again")
    elif new_ad > 1:
        print("Found %d new ads. Sending email" % new_ad)
        mail(message)
        print("Will wait for an hour before searching again")
    if old_ad == 1:
        print("Found %d old ad. Retry in one hour." % old_ad)
    elif old_ad > 1:
        print("Found %d old ads. Retry in one hour." % old_ad)

    print("The time is now " + time.strftime("%X"))
    time.sleep(int(waiting_time))
    main()
    conn.close()  # Database actually never closes.


def create_db(database):
    if os.path.exists(database):
        print("")
    else:
        conn = sqlite3.connect(database)
        print("Creating a table in database.")
        conn.execute("CREATE TABLE Items\n"
                     "(Id INT PRIMARY KEY NOT NULL,\n"
                     "Location	TEXT	NOT NULL,\n"
                     "Name		TEXT	NOT NULL,\n"
                     "Url		TEXT	NOT NULL);")
        conn.execute("CREATE TABLE New_Ads\n"
                     "(Id INT PRIMARY KEY NOT NULL,\n"
                     "Message		TEXT	NOT NULL);")
        conn.close()


def create_message(ad_id, location, name, url):
    ad = ad_id + "\n" + location + "\n" + name + "\n" + url
    message = str(ad) + "\n\n"
    return message


def mail(content):
    # to = email
    subject = "New ad found on gumtree"
    text = content

    email, password, waiting_time = get_config()

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(email, password)

    body = "\r\n".join(["To: %s" % email,
                        "From: %s" % email,
                        "Subject: %s" % subject,
                        "", text])
    try:
        server.sendmail(email, [email], body)
        print("email sent")
    except smtplib.SMTPException:
        print("error sending email")
    server.quit()


def get_config(my_waiting_time=3600):
    # Need to check if file exists, if not create one
    config_file = config_path + "gumtree.rc"
    separator = "="

    with open(config_file) as f:
        for line in f:
            current_line = line.split(separator)

            if current_line[0] == "email":
                my_email = current_line[1].strip("\n")
            elif current_line[0] == "password":
                my_password = current_line[1].strip("\n")
            elif current_line[0] == "waiting_time":
                my_waiting_time = current_line[1].strip("\n")
            else:
                print("Something's wrong")

    return my_email, my_password, my_waiting_time


if __name__ == "__main__":
    main()
