"""Script for running crawlers and notifying me via Telegram."""

import os
from time import sleep

import requests
import reddit
import invision


TELEGRAM = f"https://api.telegram.org/bot{os.environ['TOKEN']}/sendMessage"
TG_DATA = {
	'chat_id': os.environ['ME'],
	'parse_mode': 'html',
	'disable_web_page_preview': True,
}
FIVE_MINUTES = 60 * 5


def send_message(message, tries=0):
	try:
		print(message)
		response = requests.post(TELEGRAM, json=TG_DATA | {'text': message})
		response.raise_for_status()
	except requests.exceptions.RequestException:
		sleep(FIVE_MINUTES * tries)
		send_message(message, tries + 1)


def main():
	errors_count = 0
	while True:
		for site in (reddit, invision):
			try:
				for new_post in site.new_posts_checker():
					send_message(new_post)
			except requests.exceptions.RequestException as e:
				errors_count += 1
				if errors_count in (12, 120):
					send_message("Something going wrong:\n" + str(e.args))
		sleep(FIVE_MINUTES)


if __name__ == "__main__":
	main()
