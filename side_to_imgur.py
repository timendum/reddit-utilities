"""Sync image from sidebar to putre image hosting."""
from datetime import datetime

import requests
from praw import Reddit


def find_image_urls(subreddit: str):
    images = []
    reddit = Reddit()
    widgets = reddit.subreddit(subreddit).widgets
    widgets.progressive_images = False
    for widget in widgets.sidebar:
        if widget.kind != "image":
            continue
        for row in widget.data:
            images.append((row.url, row.linkUrl))
    return images


def upload_to_imgur(images):
    config = Reddit().config.custom
    refresh_req = requests.post(
        "https://api.imgur.com/oauth2/token",
        data={
            "refresh_token": config["imgur_refresh_token"],
            "client_id": config["imgur_client_id"],
            "client_secret": config["imgur_client_secret"],
            "grant_type": "refresh_token",
        },
    )
    access_token = refresh_req.json()["access_token"]
    sess = requests.session()
    sess.headers.update({"Authorization": "Bearer " + access_token})
    album_req = sess.get("https://api.imgur.com/3/album/" + config["imgur_album"])
    album = album_req.json()["data"]
    names_in_album = set([image["title"] for image in album["images"]])
    uploaded_ids = []
    for url, text in images:
        name = url.split("/")[-1].split(".")[0]
        if name in names_in_album:
            continue
        rimg = requests.get(url)
        rupload = sess.post(
            "https://api.imgur.com/3/upload", files={"image": rimg.content, "title": name}
        )
        imgid = rupload.json()["data"]["id"]
        uploaded_ids.append(imgid)
        # imgid = rupload.json()['data']['deletehash']
        description = datetime.now().strftime("%Y/%m/%d") + "\n" + text
        editreq = sess.put(
            "https://api.imgur.com/3/image/" + imgid,
            data={
                "title": name,
                "description": description,
            },
        )
        editreq.raise_for_status()
    if uploaded_ids:
        old_ids = [i["id"] for i in album["images"]]
        album_req = sess.put(
            "https://api.imgur.com/3/album/" + config["imgur_album"],
            data={"ids[]": old_ids + uploaded_ids},
        )
        album_req.raise_for_status()


def main():
    images = find_image_urls("italy")
    upload_to_imgur(images)
