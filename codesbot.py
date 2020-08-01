"""Monitoring some forum thread for some useful info"""

import os
from time import sleep

import requests
from lxml import html
from lxml.html.clean import Cleaner

##############################

TELEGRAM = f"https://api.telegram.org/bot{os.environ['TOKEN']}/sendMessage"
ME = os.environ['ME']
WEBSITE = os.environ['WEBSITE']
FORUM_PAGE = f"{WEBSITE}/forums/topic/{os.environ['THREAD_ID']}"
HEADERS = {
	'User-Agent': (
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
		'AppleWebKit/537.36 (KHTML, like Gecko) '
		'Chrome/83.0.4103.116 Safari/537.36'
	)
}
FIVE_MINS = 60 * 5
ONE_HOUR = 60 * 60
CLEANER = Cleaner(
	remove_tags=['span', 'time', 'br', 'font'],
	safe_attrs=['href']
)

##############################


def send_message(message):
	data = {
		'chat_id': ME,
		'text': message,
		'parse_mode': 'html',
		'disable_web_page_preview': True,
	}
	try:
		requests.post(TELEGRAM, data=data)
	except Exception as err:  # pylint: disable=broad-except
		print(err.args)


def get_page(page_url):
	try:
		page = requests.get(page_url, headers=HEADERS)
	except requests.exceptions.RequestException as err:
		send_message(err.args[0])
		sleep(FIVE_MINS)
		return get_page(page_url)
	if not page.ok:
		send_message(str(page.status_code))
		sleep(ONE_HOUR)
		return get_page(page_url)
	return page.content.decode('utf-8')


def parse_comment_elements(elements):
	for e in elements:
		if e.tag == 'a':
			# replace relative url with absolute
			if (href := e.get('href', "")).startswith('/'):
				e.set('href', f'{WEBSITE}/{href}')

			# replace image with placeholder text
			for img in e.iterchildren(tag='img'):
				img.tag = 'b'
				img.text = '[IMG]'
		yield html.tostring(e, encoding='unicode').strip()


def parse_comment(comment):
	comment_url_tag = comment.xpath(".//div[@class='ipsType_reset']/a")[0]
	comment_url = comment_url_tag.get('href')
	comment_time = next(comment_url_tag.iterchildren()).get('title').strip()
	cleaned_comment = CLEANER.clean_html(comment)
	comment_author = html.tostring(
		cleaned_comment.xpath(".//aside/div/h3/strong")[0],
		encoding='unicode', with_tail=False
	)
	message = f'{comment_author} (<a href="{comment_url}">{comment_time}</a>):\n'
	for paragraph in cleaned_comment.xpath(".//p"):
		paragraph_text = (
			(paragraph.text.strip() if paragraph.text else "")
			+ ' '.join(parse_comment_elements(paragraph.getchildren()))
			+ (paragraph.tail.strip() if paragraph.tail else "")
		)
		if paragraph_text:
			# mark forum quotations as Telegram code blocks
			if paragraph.getparent().getparent().tag == 'blockquote':
				paragraph_text = f'<code>{paragraph_text}</code>'
			message += '\n' + paragraph_text
	return message


def main():
	page_url = FORUM_PAGE
	last_comment_id = None

	while True:
		page = html.fromstring(get_page(page_url))

		# check if it's the last page
		if last_page_button := page.xpath("//link[@rel='last']"):
			last_page_url = last_page_button[0].get('href')
			page = html.fromstring(get_page(last_page_url))
			page_url = last_page_url

		if comments := page.xpath("//article"):
			if not last_comment_id:
				last_comment_id = int(comments[-1].attrib.get('id').split('_')[-1])
				send_message(
					"<b>Restarted. Last comment:</b>\n"
					+ parse_comment(comments[-1])
				)
			else:
				for comment in comments:
					comment_id = int(comment.attrib.get('id').split('_')[-1])
					if comment_id > last_comment_id:
						last_comment_id = comment_id
						send_message(parse_comment(comment))

		sleep(FIVE_MINS)


if __name__ == "__main__":
	main()
