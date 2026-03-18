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
    Fetch TRM from the Superfinanciera API and store in database.

    This is an optional utility function that can be called as a periodic task
    to automatically update TRM values. Currently not used by the main automation.

    Returns:
        dict: Result with 'success' and 'message' keys
    """
    try:
        # Call the TRM API
        response = requests.get(
            'https://trm-colombia.vercel.app/',
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        valor = data.get('valor')  # e.g., 4200.25
        fecha_str = data.get('fecha')  # e.g., "2026-03-15"

        if not valor or not fecha_str:
            return {
                'success': False,
                'message': 'Invalid response from TRM API'
            }

        # Parse the date
        from datetime import datetime
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

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
            'message': f"TRM {'created' if created else 'updated'} for {fecha}: {valor}",
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
