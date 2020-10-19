"""Get new posts from Reddit."""

import os
import requests


HEADER = {
	'User-Agent':
		"Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; FSL 7.0.6.01001)"
}
SUBREDDIT = os.environ['SUBREDDIT']
SUBREDDIT_URL = f"https://reddit.com/r/{os.environ['SUBREDDIT']}"
NEW_POSTS_URL = SUBREDDIT_URL + "/new.json"


def get_post(post_id):
	response = requests.get(f"{SUBREDDIT_URL}/{post_id}.json", headers=HEADER)
	response.raise_for_status()
	post = response.json()[0]['data']['children'][0]['data']
	message =\
		f"Reddit (<a href='{SUBREDDIT_URL}/comments/{post_id}'>{SUBREDDIT}</a>):\n\n"
	if post_url := post.get('url_overridden_by_dest'):
		message += f"<a href='{post_url}'>{post['title']}</a>"
	else:
		message += f"<b>{post['title']}</b>"
	if post_text := post.get('selftext'):
		message += post_text
	return message


def new_posts_checker():
	response = requests.get(NEW_POSTS_URL, headers=HEADER)
	response.raise_for_status()
	new_posts = response.json()['data']['children']
	new_posts_ids = set(post['data']['id'] for post in new_posts)
	try:
		if new_posts_ids == new_posts_checker.seen_ids:
			return
	except AttributeError:
		yield get_post(new_posts[0]['data']['id'])
	else:
		for post_id in new_posts_ids - new_posts_checker.seen_ids:
			yield get_post(post_id)
	new_posts_checker.seen_ids = new_posts_ids
