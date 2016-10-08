# L

[![Code Issues](https://www.quantifiedcode.com/api/v1/project/19cd4784a9b4456c94513fa1ecc77034/badge.svg)](https://www.quantifiedcode.com/app/project/19cd4784a9b4456c94513fa1ecc77034)
[![Build Status](https://travis-ci.org/vaultah/L.svg?branch=master)](https://travis-ci.org/vaultah/L)

This project is distributed with some other open-source components, see [credits](CREDITS.md).

***tl;dr*** This was a project I used to improve my programming skills and learn new software. Please don't use it to assess my web development skills. 

------------------

The idea was to create an open-source social network.

After 4 years of active development, it become apparent that L has no future. In addition to that, I made some bad design choices I don't have enough time/energy to fix. I've lost my motivation and enthusiasm, and I decided to drop it.

The Python code in L works fine, but browser-side code is a disaster. It's awful and it doesn't even work properly. Screenshots below are from [this](https://github.com/vaultah/L/tree/a89ec10d4d9bdd2bcf650597e6e8bbde97e8f610) revision.


##Timeline:

- I began learning PHP using [Robin Nixon's book](http://lpmj.net/4thedition). The last example (a very simple social network) became the base of this project
- Replaced old `mysqli` code with PDO
- Came up with a design
- I learned about the MVC pattern, created my own incredibly simple MVC framework and integrated it into the project
- I discovered Python and reimplemented the project in Python 3 (Bottle framework)
- I started learning NodeJS and created a basic server for push notifications
- Switched from MySQL to MongoDB
- Redesigned the project completely
- Started using a VCS
- Reimplemented the push server in Python
- Started developing a basic search engine in C++ (old source code can be found [here](https://github.com/vaultah/hasty/tree/fd19f4620d238ad350a9352fc68e82c60012c415))
- Part of browser-side JS code was rewritten in ES6
- Integrated Gulp, Babel, JSHint etc.
- Decided to use Redis instead of MongoDB. Spent some time searching for a suitable ORM-like library, but gave up and built [Fused](https://github.com/vaultah/fused). Did not finish the actual conversion (`redis` branch)

----------------------------



Here's how it looked in the end


![](http://i.imgur.com/cAsKmBt.jpg)

![](http://i.imgur.com/MowTcKu.png)

![](http://i.imgur.com/1aZOpRG.png)

![](http://i.imgur.com/ZH3WF8O.png)

