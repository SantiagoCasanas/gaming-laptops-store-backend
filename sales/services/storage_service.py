import io
from pathlib import Path
import boto3
from django.conf import settings


# ─────────────────────────────────────────────
# Public interface — callers use these two only
# ─────────────────────────────────────────────

def save_invoice(file_buffer: io.BytesIO, bill_id: str) -> str:
    """
    Persist the invoice .docx file.
    - DEBUG=True  → saves to MEDIA_ROOT/facturas/{bill_id}.docx
    - DEBUG=False → uploads to Cloudflare R2
    Returns the relative file path/key stored in `Invoice.file_path`.
    """
    if settings.DEBUG:
        return _save_locally(file_buffer, bill_id)
    return _upload_to_r2(file_buffer, bill_id)


def get_invoice_bytes(file_path: str) -> bytes:
    """
    Retrieve the invoice .docx file as bytes.
    - DEBUG=True  → reads from MEDIA_ROOT
    - DEBUG=False → downloads from Cloudflare R2
    """
    if settings.DEBUG:
        return _read_locally(file_path)
    return _download_from_r2(file_path)


# ─────────────────────────────────────────────
# Local storage (DEBUG only)
# ─────────────────────────────────────────────

def _save_locally(file_buffer: io.BytesIO, bill_id: str) -> str:
    facturas_dir = Path(settings.MEDIA_ROOT) / 'facturas'
    facturas_dir.mkdir(parents=True, exist_ok=True)
    dest = facturas_dir / f"{bill_id}.docx"
    file_buffer.seek(0)
    with open(dest, 'wb') as f:
        f.write(file_buffer.read())
    return f"facturas/{bill_id}.docx"


def _read_locally(file_path: str) -> bytes:
    full_path = Path(settings.MEDIA_ROOT) / file_path
    with open(full_path, 'rb') as f:
        return f.read()


# ─────────────────────────────────────────────
# Cloudflare R2 (production only)
# ─────────────────────────────────────────────

def _get_r2_client():
    return boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name='auto',
    )


def _upload_to_r2(file_buffer: io.BytesIO, bill_id: str) -> str:
    client = _get_r2_client()
    file_key = f"facturas/{bill_id}.docx"
    file_buffer.seek(0)
    client.upload_fileobj(
        file_buffer,
        settings.R2_BUCKET_NAME,
        file_key,
        ExtraArgs={
            'ContentType': (
                'application/vnd.openxmlformats-officedocument'
                '.wordprocessingml.document'
            ),
        },
    )
    return file_key


def _download_from_r2(file_key: str) -> bytes:
    client = _get_r2_client()
    response = client.get_object(Bucket=settings.R2_BUCKET_NAME, Key=file_key)
    return response['Body'].read()
