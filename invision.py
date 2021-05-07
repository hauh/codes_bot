"""Get new posts from Invision-made forum topic."""

import os

import requests
from lxml import html
from lxml.html.clean import Cleaner

WEBSITE = "https://" + os.environ['WEBSITE']
FORUM_PAGE = (
	f"{WEBSITE}/index.php?app=forums&controller=topic"
	f"&id={os.environ['TOPIC_ID']}&page=1000"  # 1000 will redirect to last page
)
HEADERS = {
	'User-Agent': (
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
		'AppleWebKit/537.36 (KHTML, like Gecko) '
		'Chrome/83.0.4103.116 Safari/537.36'
	)
}
FIVE_MINS = 60 * 5
CLEANER = Cleaner(
	remove_tags=['span', 'time', 'br', 'font'],
	safe_attrs=['href']
)


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


def parse_paragraph(paragraph):
	paragraph_text = (
		(paragraph.text.strip() if paragraph.text else "")
		+ ' '.join(parse_comment_elements(paragraph.getchildren()))
		+ (paragraph.tail.strip() if paragraph.tail else "")
	)
	if paragraph_text:
		# mark forum quotations as Telegram code blocks
		grandparent = paragraph.getparent().getparent()
		if grandparent is not None and grandparent.tag == 'blockquote':
			paragraph_text = f'<code>{paragraph_text}</code>'
	return paragraph_text


def parse_table(table):
	lines = []
	table = table.find('tbody')
	for tr in table.iterchildren('tr'):
		cells = []
		for td in tr.iterchildren('td'):
			if cell_text := td.text.strip():
				cells.append(cell_text)
		lines.append('\t'.join(cells))
	return '<code>' + '\n'.join(lines) + '</code>'


def parse_comment(comment):
	author = comment.xpath(".//aside/div/h3/strong/a")[0].text
	url = f"{FORUM_PAGE}#{comment.getprevious().get('id')}"
	time = comment.xpath(".//time")[0].get('title')
	content = comment.xpath(".//div[@data-role='commentContent']")[0]
	cleaned_comment = CLEANER.clean_html(content)
	message_parts = [f'{author} (<a href="{url}">{time}</a>):\n']
	for comment_part in cleaned_comment.iterdescendants('p', 'table'):
		if comment_part.tag == 'p':
			parsed_part = parse_paragraph(comment_part)
		else:
			parsed_part = parse_table(comment_part)
		if parsed_part:
			message_parts.append(parsed_part)
	return '\n'.join(message_parts)


def new_posts_checker():
	response = requests.get(FORUM_PAGE, headers=HEADERS)
	response.raise_for_status()
	page = html.fromstring(response.content.decode('utf-8'))
	comments = page.xpath("//article")
	last_comment_id = int(comments[-1].attrib.get('id').split('_')[-1])
	try:
		if last_comment_id <= new_posts_checker.last_id:
			return
	except AttributeError:
		yield parse_comment(comments[-1])
	else:
		for comment in comments:
			comment_id = int(comment.attrib.get('id').split('_')[-1])
			if comment_id > new_posts_checker.last_id:
				yield parse_comment(comment)
	new_posts_checker.last_id = last_comment_id
