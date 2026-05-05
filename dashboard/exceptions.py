from rest_framework.exceptions import ValidationError


class InvalidMonthParam(ValidationError):
    """Raised when ?month= is malformed or out of range. Maps to HTTP 400."""

    def __init__(self, detail=None):
        super().__init__(
            detail or {'month': "Formato inválido. Usa YYYY-MM (ej. 2026-04)."}
        )
