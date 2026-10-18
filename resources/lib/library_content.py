"""Validate skin-owned inputs. Providers retain metadata and playback ownership."""
import re
from urllib.parse import parse_qs, urlencode, urlsplit

PKC = 'plugin://plugin.video.plexkodiconnect/starlight/'
HUBS = ('trending', 'movies', 'tvshows', 'upcoming', 'top_rated')


def provider_item(path):
    """Accept one PKC item identity without executable command characters."""
    parsed = urlsplit(path)
    if (parsed.scheme != 'plugin' or parsed.netloc != 'plugin.video.plexkodiconnect'
            or parsed.path != '/starlight/item' or parsed.fragment):
        return None
    args = parse_qs(parsed.query, keep_blank_values=True)
    keys = args.get('rating_key', [])
    if set(args) != {'rating_key'} or len(keys) != 1 or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', keys[0]):
        return None
    return PKC + 'item?' + urlencode({'rating_key': keys[0]})


def board_rows(records, part):
    """Partition one ordered provider snapshot without duplicate Board cards."""
    if part == 'feature':
        return records[:1]
    if part == 'tiles':
        return records[1:5]
    if part == 'row':
        return records[5:]
    raise ValueError('Unknown Board partition')


def edit_query(query, key):
    """Apply one strip key within the search contract's text limit."""
    if key == 'delete':
        return query[:-1]
    if key == 'space':
        return (query + ' ')[:256]
    if len(key) == 1 and key in 'abcdefghijklmnopqrstuvwxyz0123456789':
        return (query + key)[:256]
    raise ValueError('Unknown search character')
