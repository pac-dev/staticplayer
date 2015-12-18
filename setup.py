#!/usr/bin/env python

from distutils.core import setup

setup(
	name='staticplayer',
	version='1.0',
	description='Static Online Playlist Generator',
	author_email='pierre@osar.fr',
	url='https://github.com/pac/staticplayer',
	install_requires=[
		'jinja2',
		'pyyaml',
		'mutagen',
	]
)