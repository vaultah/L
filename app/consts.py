import os
import string
import json
from pathlib import Path, PurePath
from collections import OrderedDict
from enum import IntEnum

# These paths are fixed or very unlikely to get changed

ROOT = Path(__file__).resolve().parent.parent

# Path to generated config
CONFIG = ROOT / 'L-config'

L_ROOT = ROOT / 'app'
L_VIEWS = L_ROOT / 'markup'
L_PUBLIC = ROOT / 'public'

# Just the name, hence PurePaths
ASSETS = PurePath('assets')
L_ASSETS = L_PUBLIC / ASSETS

IMAGES_DIR = 'images'
L_MEDIA = ROOT / 'L-media'
L_MEDIA_IMAGES = L_MEDIA / IMAGES_DIR

# Create dirs
for p in (L_MEDIA_IMAGES,):
    try:
        p.mkdir(parents=True)
    except FileExistsError:
        pass

# Load some info from the previously generated config
# Must be available after the 'prepare' step

with (CONFIG / 'L.json').open() as f:
    params = json.load(f)
    L_MEDIA_DOMAIN = '{media_domain}.{host}'.format_map(params)
    L_SMTP_HOST = params['smtp_host']
    L_HOST = params['host']

# Notifications

NOTIFICATIONS = IntEnum('NotificationTypes', 
                        ['mention', 'reply', 'share', 'friend',
                         'follower', 'request'])

# Min/max Lengths

WEBSITE_LENGTH = [3, 50]
NAME_MAXLENGTH = 40
USR_LENGTH = [5, 32]
PWD_LENGTH = [7, 250]
EMAIL_LENGTH = [6, 60]
POST_MAXLENGTH = 5000
MSG_MAXLENGTH = 2000

# Content types
# TODO: Think about using enum
CONTENT_IMAGE = 1
CONTENT_POST = 2

CONTENT_TYPES = {
    'image': CONTENT_IMAGE,
    'post': CONTENT_POST
}

CONTENT_TYPES_JSON = json.dumps(CONTENT_TYPES)

# # Global types
# CONTENT_TYPES = IntEnum('ContentTypes', 'image post')
# CONTENT_TYPES_JSON = json.dumps(dict(CONTENT_TYPES.__members__))

# Images

AVATAR = 'avatar'
ORIGINAL_IMAGE = 'large'
COVER_IMAGE = 'cover'
SQUARE_THUMBNAIL = 'thumb'
SHRINKED_IMAGE = 'shrinked'
SHRINKED_WIDTH = 750
MAX_FILE_SIZE = 10*1024*1024
COVER_RATIO = [7, 2]
IMG_DELETION_MAX = 150
DEFAULT_AVATAR = PurePath('/') / ASSETS / 'images' / 'default.png'

# We convert random ints to the base N (N = len(BASE_CONVERSION_TABLE)) using
# this conversion table

BASE_CONVERSION_TABLE = string.digits + string.ascii_lowercase
NAME_CHARACTERS = frozenset(string.ascii_letters + string.digits + '-_')

# Content type -> (DB name, collections's name)
# TODO: Currently limited to one host
MONGO = {
    'posts': ('media', 'published'),
    'images': ('media', 'images'),
    'feed': ('media', 'feed'),
    'records': ('main', 'records'),
    'notifications': ('main', 'notifications'),
    'cookies': ('main', 'cookies'),
    'reset': ('main', 'reset'),
    'requests': ('main', 'requests'),
    'friends': ('main', 'friends'),
    'followers': ('main', 'followers'),
    'blocked': ('main', 'blocked'),
    'ratings': ('main', 'ratings'),
}


# OrderedDict of countries

COUNTRIES = OrderedDict([
    ("", "Choose your country from this list"),
    ("us", "United States"),
    ("gb", "United Kingdom"),
    ("ru", "Russia"),
    ("ca", "Canada"),
    ("fr", "France"),
    ("af", "Afghanistan"),
    ("ax", "Åland Islands"),
    ("al", "Albania"),
    ("dz", "Algeria"),
    ("as", "American Samoa"),
    ("ad", "Andorra"),
    ("ao", "Angola"),
    ("ai", "Anguilla"),
    ("aq", "Antarctica"),
    ("ag", "Antigua and Barbuda"),
    ("ar", "Argentina"),
    ("am", "Armenia"),
    ("aw", "Aruba"),
    ("au", "Australia"),
    ("at", "Austria"),
    ("az", "Azerbaijan"),
    ("bs", "Bahamas"),
    ("bh", "Bahrain"),
    ("bd", "Bangladesh"),
    ("bb", "Barbados"),
    ("by", "Belarus"),
    ("be", "Belgium"),
    ("bz", "Belize"),
    ("bj", "Benin"),
    ("bm", "Bermuda"),
    ("bt", "Bhutan"),
    ("bo", "Bolivia"),
    ("ba", "Bosnia and Herzegovina"),
    ("bw", "Botswana"),
    ("bv", "Bouvet Island"),
    ("br", "Brazil"),
    ("io", "British Indian Ocean Territory"),
    ("bn", "Brunei Darussalam"),
    ("bg", "Bulgaria"),
    ("bf", "Burkina Faso"),
    ("bi", "Burundi"),
    ("kh", "Cambodia"),
    ("cm", "Cameroon"),
    ("cv", "Cape Verde"),
    ("ky", "Cayman Islands"),
    ("cf", "Central African Republic"),
    ("td", "Chad"),
    ("cl", "Chile"),
    ("cn", "China"),
    ("cx", "Christmas Island"),
    ("cc", "Cocos(Keeling) Islands"),
    ("co", "Colombia"),
    ("km", "Comoros"),
    ("cg", "Congo"),
    ("cd", "Congo, The Democratic Republic of The"),
    ("ck", "Cook Islands"),
    ("cr", "Costa Rica"),
    ("ci", "Cote D'ivoire"),
    ("hr", "Croatia"),
    ("cu", "Cuba"),
    ("cy", "Cyprus"),
    ("cz", "Czech Republic"),
    ("dk", "Denmark"),
    ("dj", "Djibouti"),
    ("dm", "Dominica"),
    ("do", "Dominican Republic"),
    ("ec", "Ecuador"),
    ("eg", "Egypt"),
    ("sv", "El Salvador"),
    ("gq", "Equatorial Guinea"),
    ("er", "Eritrea"),
    ("ee", "Estonia"),
    ("et", "Ethiopia"),
    ("fk", "Falkland Islands(Malvinas)"),
    ("fo", "Faroe Islands"),
    ("fj", "Fiji"),
    ("fi", "Finland"),
    ("gf", "French Guiana"),
    ("pf", "French Polynesia"),
    ("tf", "French Southern Territories"),
    ("ga", "Gabon"),
    ("gm", "Gambia"),
    ("ge", "Georgia"),
    ("de", "Germany"),
    ("gh", "Ghana"),
    ("gi", "Gibraltar"),
    ("gr", "Greece"),
    ("gl", "Greenland"),
    ("gd", "Grenada"),
    ("gp", "Guadeloupe"),
    ("gu", "Guam"),
    ("gt", "Guatemala"),
    ("gg", "Guernsey"),
    ("gn", "Guinea"),
    ("gw", "Guinea-bissau"),
    ("gy", "Guyana"),
    ("ht", "Haiti"),
    ("hm", "Heard Island and Mcdonald Islands"),
    ("va", "Holy See(Vatican City State)"),
    ("hn", "Honduras"),
    ("hk", "Hong Kong"),
    ("hu", "Hungary"),
    ("is", "Iceland"),
    ("in", "India"),
    ("id", "Indonesia"),
    ("ir", "Iran, Islamic Republic of"),
    ("iq", "Iraq"),
    ("ie", "Ireland"),
    ("im", "Isle of Man"),
    ("il", "Israel"),
    ("it", "Italy"),
    ("jm", "Jamaica"),
    ("jp", "Japan"),
    ("je", "Jersey"),
    ("jo", "Jordan"),
    ("kz", "Kazakhstan"),
    ("ke", "Kenya"),
    ("ki", "Kiribati"),
    ("kp", "Korea, Democratic People's Republic of"),
    ("kr", "Korea, Republic of"),
    ("kw", "Kuwait"),
    ("kg", "Kyrgyzstan"),
    ("la", "Lao People's Democratic Republic"),
    ("lv", "Latvia"),
    ("lb", "Lebanon"),
    ("ls", "Lesotho"),
    ("lr", "Liberia"),
    ("ly", "Libyan Arab Jamahiriya"),
    ("li", "Liechtenstein"),
    ("lt", "Lithuania"),
    ("lu", "Luxembourg"),
    ("mo", "Macao"),
    ("mk", "Macedonia, The Former Yugoslav Republic of"),
    ("mg", "Madagascar"),
    ("mw", "Malawi"),
    ("my", "Malaysia"),
    ("mv", "Maldives"),
    ("ml", "Mali"),
    ("mt", "Malta"),
    ("mh", "Marshall Islands"),
    ("mq", "Martinique"),
    ("mr", "Mauritania"),
    ("mu", "Mauritius"),
    ("yt", "Mayotte"),
    ("mx", "Mexico"),
    ("fm", "Micronesia, Federated States of"),
    ("md", "Moldova, Republic of"),
    ("mc", "Monaco"),
    ("mn", "Mongolia"),
    ("me", "Montenegro"),
    ("ms", "Montserrat"),
    ("ma", "Morocco"),
    ("mz", "Mozambique"),
    ("mm", "Myanmar"),
    ("na", "Namibia"),
    ("nr", "Nauru"),
    ("np", "Nepal"),
    ("nl", "Netherlands"),
    ("an", "Netherlands Antilles"),
    ("nc", "New Caledonia"),
    ("nz", "New Zealand"),
    ("ni", "Nicaragua"),
    ("ne", "Niger"),
    ("ng", "Nigeria"),
    ("nu", "Niue"),
    ("nf", "Norfolk Island"),
    ("mp", "Northern Mariana Islands"),
    ("no", "Norway"),
    ("om", "Oman"),
    ("pk", "Pakistan"),
    ("pw", "Palau"),
    ("ps", "Palestinian Territory, Occupied"),
    ("pa", "Panama"),
    ("pg", "Papua New Guinea"),
    ("py", "Paraguay"),
    ("pe", "Peru"),
    ("ph", "Philippines"),
    ("pn", "Pitcairn"),
    ("pl", "Poland"),
    ("pt", "Portugal"),
    ("pr", "Puerto Rico"),
    ("qa", "Qatar"),
    ("re", "Reunion"),
    ("ro", "Romania"),
    ("rw", "Rwanda"),
    ("sh", "Saint Helena"),
    ("kn", "Saint Kitts and Nevis"),
    ("lc", "Saint Lucia"),
    ("pm", "Saint Pierre and Miquelon"),
    ("vc", "Saint Vincent and The Grenadines"),
    ("ws", "Samoa"),
    ("sm", "San Marino"),
    ("st", "Sao Tome and Principe"),
    ("sa", "Saudi Arabia"),
    ("sn", "Senegal"),
    ("rs", "Serbia"),
    ("sc", "Seychelles"),
    ("sl", "Sierra Leone"),
    ("sg", "Singapore"),
    ("sk", "Slovakia"),
    ("si", "Slovenia"),
    ("sb", "Solomon Islands"),
    ("so", "Somalia"),
    ("za", "South Africa"),
    ("gs", "South Georgia and The South Sandwich Islands"),
    ("es", "Spain"),
    ("lk", "Sri Lanka"),
    ("sd", "Sudan"),
    ("sr", "Suriname"),
    ("sj", "Svalbard and Jan Mayen"),
    ("sz", "Swaziland"),
    ("se", "Sweden"),
    ("ch", "Switzerland"),
    ("sy", "Syrian Arab Republic"),
    ("tw", "Taiwan, Province of China"),
    ("tj", "Tajikistan"),
    ("tz", "Tanzania, United Republic of"),
    ("th", "Thailand"),
    ("tl", "Timor-leste"),
    ("tg", "Togo"),
    ("tk", "Tokelau"),
    ("to", "Tonga"),
    ("tt", "Trinidad and Tobago"),
    ("tn", "Tunisia"),
    ("tr", "Turkey"),
    ("tm", "Turkmenistan"),
    ("tc", "Turks and Caicos Islands"),
    ("tv", "Tuvalu"),
    ("ug", "Uganda"),
    ("ua", "Ukraine"),
    ("ae", "United Arab Emirates"),
    ("um", "United States Minor Outlying Islands"),
    ("uy", "Uruguay"),
    ("uz", "Uzbekistan"),
    ("vu", "Vanuatu"),
    ("ve", "Venezuela"),
    ("vn", "Viet Nam"),
    ("vg", "Virgin Islands, British"),
    ("vi", "Virgin Islands, U.S."),
    ("wf", "Wallis and Futuna"),
    ("eh", "Western Sahara"),
    ("ye", "Yemen"),
    ("zm", "Zambia"),
    ("zw", "Zimbabwe")
])
