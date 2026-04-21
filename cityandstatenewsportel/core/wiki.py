"""
Wikipedia & Wikidata API helpers with Django cache.
All functions handle errors gracefully — return None on failure.
"""
import urllib.request
import urllib.parse
import json
import re
from django.core.cache import cache

TIMEOUT   = 8     # HTTP request timeout (seconds)
CACHE_TTL = 3600  # Cache duration: 1 hour


# ── Internal HTTP helper ───────────────────────────────────────────────────────
def _get(url):
    """GET request → parsed JSON. Returns None on any error."""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'DailyPortal/1.0 (news portal; educational)'}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception:
        return None


# ── AI-style summary generator (no external API needed) ───────────────────────
def generate_ai_summary(text, max_sentences=2):
    """
    Generate a short summary from a longer text by extracting
    the most informative sentences (extractive summarization).
    """
    if not text:
        return ''
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Score each sentence by length (longer = more info, up to a limit)
    scored = [(len(s.split()), s) for s in sentences if len(s.split()) > 5]
    scored.sort(reverse=True)
    # Take top N sentences in original order
    top = set(s for _, s in scored[:max_sentences])
    summary = ' '.join(s for s in sentences if s in top)
    return summary[:300] if summary else sentences[0][:300]


# ── Wikipedia REST API ─────────────────────────────────────────────────────────
def get_wiki_summary(city_name):
    """
    Fetch Wikipedia page summary for a city/place.

    API: https://en.wikipedia.org/api/rest_v1/page/summary/{title}

    Returns dict:
        title, description, extract, ai_summary,
        thumbnail, wiki_url, coordinates
    Returns None if not found or on error.
    """
    cache_key = f'wiki_summary_{city_name.strip().lower()}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    slug = urllib.parse.quote(city_name.strip().replace(' ', '_'))
    url  = f'https://en.wikipedia.org/api/rest_v1/page/summary/{slug}'
    data = _get(url)

    # Not found or error
    if not data or 'not_found' in str(data.get('type', '')):
        cache.set(cache_key, None, 300)   # cache miss for 5 min
        return None

    extract = data.get('extract', '')

    result = {
        'title':       data.get('title', city_name),
        'description': data.get('description', ''),
        'extract':     extract[:600],
        'ai_summary':  generate_ai_summary(extract),   # short AI-style summary
        'thumbnail':   (data.get('thumbnail') or {}).get('source'),
        'wiki_url':    (data.get('content_urls') or {}).get('desktop', {}).get('page', ''),
        'coordinates': data.get('coordinates'),        # {'lat': ..., 'lon': ...}
    }
    cache.set(cache_key, result, CACHE_TTL)
    return result


# ── Wikidata SPARQL API ────────────────────────────────────────────────────────
def get_wikidata_facts(city_name):
    """
    Fetch structured facts from Wikidata via SPARQL endpoint.

    API: https://query.wikidata.org/sparql

    Returns dict:
        population, area, country, state, founded
    Returns None if no data found.
    """
    cache_key = f'wikidata_facts_{city_name.strip().lower()}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    sparql = f"""
    SELECT ?pop ?area ?countryLabel ?stateLabel ?founded WHERE {{
      ?city rdfs:label "{city_name}"@en .
      OPTIONAL {{ ?city wdt:P1082 ?pop . }}
      OPTIONAL {{ ?city wdt:P2046 ?area . }}
      OPTIONAL {{
        ?city wdt:P17 ?country .
        ?country rdfs:label ?countryLabel FILTER(LANG(?countryLabel) = "en")
      }}
      OPTIONAL {{
        ?city wdt:P131 ?state .
        ?state rdfs:label ?stateLabel FILTER(LANG(?stateLabel) = "en")
      }}
      OPTIONAL {{ ?city wdt:P571 ?founded . }}
    }} LIMIT 1
    """
    url  = 'https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(sparql)
    data = _get(url)

    if not data:
        cache.set(cache_key, None, 300)
        return None

    bindings = data.get('results', {}).get('bindings', [])
    if not bindings:
        cache.set(cache_key, None, 300)
        return None

    b = bindings[0]
    def val(f): return b.get(f, {}).get('value')

    pop     = val('pop')
    area    = val('area')
    founded = val('founded')

    result = {
        'population': f"{int(float(pop)):,}"      if pop     else None,
        'area':       f"{float(area):.1f} km²"    if area    else None,
        'country':    val('countryLabel'),
        'state':      val('stateLabel'),
        'founded':    founded[:4]                  if founded else None,
    }
    cache.set(cache_key, result, CACHE_TTL)
    return result


# ── Wikipedia Search ───────────────────────────────────────────────────────────
def search_wikipedia(query, limit=5):
    """
    Search Wikipedia for pages matching a query.
    Used for the dynamic city search feature.

    Returns list of dicts: title, description, thumbnail, wiki_url
    """
    cache_key = f'wiki_search_{query.strip().lower()}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    slug = urllib.parse.quote(query.strip())
    url  = f'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={slug}&format=json&srlimit={limit}'
    data = _get(url)

    if not data:
        return []

    results = []
    for item in data.get('query', {}).get('search', []):
        title = item.get('title', '')
        # Clean HTML from snippet
        snippet = re.sub(r'<[^>]+>', '', item.get('snippet', ''))
        results.append({
            'title':    title,
            'snippet':  snippet,
            'wiki_url': f'https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(" ", "_"))}',
        })

    cache.set(cache_key, results, CACHE_TTL)
    return results


# ── Trending cities helper ─────────────────────────────────────────────────────
def get_trending_cities_info(city_list):
    """
    Fetch Wikipedia summaries for a list of cities in bulk.
    Returns list of wiki summary dicts (skips cities with no data).
    """
    results = []
    for city in city_list[:6]:   # cap at 6 to avoid slow loads
        info = get_wiki_summary(city)
        if info:
            info['city_name'] = city
            results.append(info)
    return results


# ── Combined city info ─────────────────────────────────────────────────────────
def get_city_info(city_name):
    """
    Combined call — returns both wiki summary and wikidata facts.
    Always returns a dict (values may be None).
    """
    return {
        'wiki':     get_wiki_summary(city_name),
        'wikidata': get_wikidata_facts(city_name),
    }
