import logging
import resend
from django.conf import settings

logger = logging.getLogger(__name__)


def send_invoice_email(invoice, file_bytes: bytes) -> bool:
    """
    Send the invoice PDF to the client via Resend.
    Returns True on success, False on any failure (error is logged).
    """
    try:
        resend.api_key = settings.RESEND_API_KEY

        concepto_display = {
            'venta': 'Venta',
            'separacion': 'Separación',
        }.get(invoice.concepto, invoice.concepto)

        item_display = {
            'laptop': 'Laptop',
            'tarjeta_grafica': 'Tarjeta Gráfica',
            'hardware': 'Hardware',
            'pc_mesa': 'PC de Mesa',
        }.get(invoice.item, invoice.item)

        payment_display = {
            'efectivo': 'Efectivo',
            'tarjeta': 'Tarjeta',
            'transferencia': 'Transferencia',
            'otro': 'Otro',
        }.get(invoice.payment_method, invoice.payment_method)

        try:
            int_amount = int(invoice.total_amount)
            formatted_amount = f"COP ${int_amount:,}".replace(',', '.')
        except (ValueError, TypeError):
            formatted_amount = str(invoice.total_amount)

        html_body = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Factura {invoice.bill_id}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
          <tr>
            <td style="background:#0A1628;padding:32px 40px;text-align:center;">
              <h1 style="color:#ffffff;margin:0;font-size:24px;letter-spacing:1px;">PATECNOLOGICOS</h1>
              <p style="color:#94a3b8;margin:8px 0 0;font-size:14px;">Tecnología Gamer de Alto Rendimiento</p>
            </td>
          </tr>
          <tr>
            <td style="padding:40px;">
              <h2 style="color:#0A1628;margin:0 0 8px;font-size:20px;">Tu Factura de Compra</h2>
              <p style="color:#64748b;margin:0 0 32px;font-size:14px;">
                Hola <strong>{invoice.client_name}</strong>, adjuntamos tu factura correspondiente a tu {concepto_display.lower()}.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0;margin-bottom:32px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <table width="100%" cellpadding="8" cellspacing="0">
                      <tr>
                        <td style="color:#64748b;font-size:13px;width:50%;">N° Factura</td>
                        <td style="color:#0A1628;font-size:13px;font-weight:bold;">{invoice.bill_id}</td>
                      </tr>
                      <tr>
                        <td style="color:#64748b;font-size:13px;">Concepto</td>
                        <td style="color:#0A1628;font-size:13px;">{concepto_display}</td>
                      </tr>
                      <tr>
                        <td style="color:#64748b;font-size:13px;">Producto</td>
                        <td style="color:#0A1628;font-size:13px;">{item_display}</td>
                      </tr>
                      <tr>
                        <td style="color:#64748b;font-size:13px;">Serial</td>
                        <td style="color:#0A1628;font-size:13px;">{invoice.serial_item}</td>
                      </tr>
                      <tr>
                        <td style="color:#64748b;font-size:13px;">Método de Pago</td>
                        <td style="color:#0A1628;font-size:13px;">{payment_display}</td>
                      </tr>
                      <tr>
                        <td style="color:#64748b;font-size:13px;">Fecha</td>
                        <td style="color:#0A1628;font-size:13px;">{invoice.due_date.strftime('%d/%m/%Y')}</td>
                      </tr>
                      <tr style="border-top:2px solid #e2e8f0;">
                        <td style="color:#0A1628;font-size:15px;font-weight:bold;padding-top:12px;">Total</td>
                        <td style="color:#0A1628;font-size:15px;font-weight:bold;padding-top:12px;">{formatted_amount}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              <p style="color:#64748b;font-size:13px;margin:0 0 8px;">
                El documento de tu factura está adjunto a este correo, descárgalo para una mejor visualización.
              </p>
              <p style="color:#64748b;font-size:13px;margin:0 0 32px;">
                Si tienes alguna pregunta, contáctanos por WhatsApp al <strong>+57 301 266 1811</strong>.
              </p>
              <p style="color:#64748b;font-size:12px;margin:0;border-top:1px solid #e2e8f0;padding-top:20px;">
                Gracias por tu compra en <strong>Patecnologicos</strong>. ¡Esperamos verte pronto!
              </p>
            </td>
          </tr>
          <tr>
            <td style="background:#f8fafc;padding:20px 40px;text-align:center;border-top:1px solid #e2e8f0;">
              <p style="color:#94a3b8;font-size:12px;margin:0;">
                © 2025 Patecnologicos. Todos los derechos reservados.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
        """

        params: resend.Emails.SendParams = {
            "from": "sales@patecnologicos.com",
            "to": [invoice.client_email],
            "subject": f"Tu factura de compra - Patecnologicos - {invoice.bill_id}",
            "html": html_body,
            "attachments": [
                {
                    "filename": f"factura_{invoice.bill_id}.docx",
                    # resend SDK v2: content must be list[int], not base64 string
                    "content": list(file_bytes),
                    "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                }
            ],
        }

        resend.Emails.send(params)
        return True

    except Exception as exc:
        logger.error("Error sending invoice email for %s: %s", invoice.bill_id, exc, exc_info=True)
        return False
