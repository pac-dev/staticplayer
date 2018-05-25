**Warning: this is pre-alpha, here be missing features**

A static online playlist generator
==================================
I made staticplayer because I wanted an simple way of uploading playlists from my audio library to a static host. It's vaguely inspired by minimalist playlists such as the infamous [Vidya Intarweb Playlist](http://vip.aersia.net/vip.swf). (But without the flash requirement!)

Demos
-----
**todo**

Getting started
---------------
- Get the python requirements:

    $ pip install jinja2 pyyaml mutagen

- Get [ffmpeg](http://ffmpeg.org/download.html). *(The staticplayer generator will run without ffmpeg, but it won't transcode input files into the required CBR mp3 format.)*

- Download or clone the staticplayer repository.

- Copy [example.yml](https://github.com/pac/staticplayer/blob/master/example.yml) and edit it to set up your playlists, title, etc. You can reference existing m3u playlists, or just list files in the config file. The comments in the example will guide you through the details.

- Generate the site:

    $ python staticplayer-gen.py my-playlists.yml

Prior art
---------
I'm a fan of [Ampache](http://ampache.github.io) and [Groovebasin](http://groovebasin.com/)! staticplayer is a much smaller project and is not an online media server, but a static site generator. In a nutshell, this means that it does not require a full server, and can instead be hosted on cheap and super-fast static file hosts (such as Amazon S3, Rackspace Cloud Files, or even Github Pages). Being static also means that it has less features, but that's, um, minimalism!
