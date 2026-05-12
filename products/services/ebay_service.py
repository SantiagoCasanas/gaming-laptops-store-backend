"""
eBay API integration service for fetching item data and managing OAuth2 tokens.
"""
import base64
import requests
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_ebay_access_token():
    """
    Fetch a new eBay OAuth2 access token using Client Credentials flow.

    Returns:
        str: OAuth2 access token

    Raises:
        requests.RequestException: If the token request fails
        ValueError: If the response doesn't contain an access_token
    """
    client_id = settings.EBAY_CLIENT_ID
    client_secret = settings.EBAY_CLIENT_SECRET

    if not client_id or not client_secret:
        raise ValueError("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are not configured")

    # Prepare Basic auth header
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    url = "https://api.ebay.com/identity/v1/oauth2/token"
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    # Public Browse API requires only the base api_scope. The buy.item.feed
    # scope needs explicit eBay approval and our app does not have it.
    data = {"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"}

    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("No access_token in eBay API response")

        return access_token

    except requests.RequestException as e:
        logger.error(f"Failed to fetch eBay access token: {str(e)}")
        raise


def get_cached_ebay_token():
    """
    Retrieve eBay access token from cache or fetch a new one if expired.

    Returns:
        str: OAuth2 access token

    Raises:
        requests.RequestException: If token fetch fails
        ValueError: If token configuration is missing
    """
    cache_key = settings.EBAY_TOKEN_CACHE_KEY
    token = cache.get(cache_key)

    if not token:
        token = get_ebay_access_token()
        cache.set(cache_key, token, settings.EBAY_TOKEN_CACHE_TIMEOUT)

    return token


def get_ebay_item_data(legacy_item_id):
    """
    Fetch item data from eBay Browse API using legacy item ID.

    Args:
        legacy_item_id: eBay legacy item ID (numeric)

    Returns:
        dict: Item data from eBay API including price and availability

    Raises:
        requests.RequestException: If API request fails
        ValueError: If item not found or API returns error
    """
    token = get_cached_ebay_token()

    url = f"https://api.ebay.com/buy/browse/v1/item/get_item_by_legacy_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    params = {
        "legacy_item_id": legacy_item_id,
        "marketplace_id": settings.EBAY_MARKETPLACE_ID,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:
        logger.error(f"Failed to fetch eBay item {legacy_item_id}: {str(e)}")
        raise


def extract_legacy_id_from_url(ebay_url):
    """
    Extract eBay legacy item ID from a product URL.

    Supports formats:
    - https://www.ebay.com/itm/123456789
    - https://www.ebay.com/itm/Product-Name/123456789
    - https://www.ebay.com/itm/123456789?var=456

    Args:
        ebay_url: eBay product URL

    Returns:
        str: Legacy item ID (numeric string)

    Raises:
        ValueError: If URL format is invalid or ID cannot be extracted
    """
    import re

    if not ebay_url:
        raise ValueError("eBay URL is empty")

    # Match pattern: /itm/123456789 or /itm/name/123456789
    match = re.search(r'/itm/(?:[^/]+/)?(\d+)', ebay_url)
    if not match:
        raise ValueError(f"Could not extract legacy ID from URL: {ebay_url}")

    return match.group(1)
