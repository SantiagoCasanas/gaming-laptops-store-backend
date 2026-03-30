"""
Service for managing TRM (USD to COP exchange rate) data.
"""
import requests
from datetime import date
from django.core.cache import cache
from core.models import TRMHistory


def get_trm_for_date(target_date):
    """
    Retrieve the TRM (exchange rate) for a specific date.

    First looks for an exact match on the given date.
    If not found, returns the most recent TRM before that date.
    If no TRM exists for that date or earlier, raises ValueError.

    Args:
        target_date: datetime.date object

    Returns:
        TRMHistory object

    Raises:
        ValueError: If no TRM found for the given date or earlier
    """
    # Try exact match first
    trm = TRMHistory.objects.filter(fecha=target_date).first()
    if trm:
        return trm

    # Get most recent TRM before the target date
    trm = (
        TRMHistory.objects
        .filter(fecha__lte=target_date)
        .order_by('-fecha')
        .first()
    )
    if trm:
        return trm

    # No TRM found
    raise ValueError(
        f"No TRM history found for date {target_date} or earlier"
    )


def fetch_and_store_trm():
    """
    Fetch TRM from the trm-colombia API and store in database.

    API: https://trm-colombia.vercel.app/?date=YYYY-MM-DD
    Response: { "data": { "value": 3704.17, "validityFrom": "2026-03-19T05:00:00.000Z", ... } }

    Returns:
        dict: Result with 'success' and 'message' keys
    """
    try:
        from datetime import datetime
        today_str = date.today().strftime('%Y-%m-%d')

        # Call the TRM API with today's date
        response = requests.get(
            f'https://trm-colombia.vercel.app/?date={today_str}',
            timeout=10
        )
        response.raise_for_status()

        payload = response.json()
        inner = payload.get('data', {})
        valor = inner.get('value')
        validity_from = inner.get('validityFrom')  # e.g. "2026-03-19T05:00:00.000Z"

        if not valor or not validity_from:
            return {
                'success': False,
                'message': f'Invalid response from TRM API: {payload}'
            }

        # Parse ISO date from validityFrom
        fecha = datetime.fromisoformat(validity_from.replace('Z', '+00:00')).date()

        # Create or update TRM record
        trm, created = TRMHistory.objects.get_or_create(
            fecha=fecha,
            defaults={
                'valor_cop': valor,
                'fuente': 'superfinanciera'
            }
        )

        return {
            'success': True,
            'message': f"TRM {'created' if created else 'already exists'} for {fecha}: {valor}",
            'trm': trm
        }

    except requests.RequestException as e:
        return {
            'success': False,
            'message': f"Failed to fetch TRM: {str(e)}"
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error storing TRM: {str(e)}"
        }
