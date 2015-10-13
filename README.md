# L

[![Code Issues](https://www.quantifiedcode.com/api/v1/project/19cd4784a9b4456c94513fa1ecc77034/badge.svg)](https://www.quantifiedcode.com/app/project/19cd4784a9b4456c94513fa1ecc77034)
[![Build Status](https://travis-ci.org/vaultah/L.svg?branch=master)](https://travis-ci.org/vaultah/L)



##Installation + deploy

We are currently using MongoDB (as a database) and Nginx (as a webserver) which we expect you to install. You're also expected to allow **L** sending email, i.e. by installing Exim or other mail server.

Additional libraries can be installed via `apt-get` (on Debian-based systems) as follows:

	~$ sudo apt-get install libjpeg-dev zlib1g-dev libpng12-dev

After all the requirements are satisfied, you can install **L**:

	~$ cd L
	~/L$ python setup.py install
	~/L$ python setup.py prepare
	~/L$ vi config/L.json # Edit generated config
	~/L$ sudo python setup.py deploy
 

We use py.test for testing. A minimal test would look like

	~/L$ py.test --pyargs app --no-send --no-urls

This project is distributed with some other open-source components, see [credits](CREDITS.md).
