web: python fix_migrations.py && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
# Las tareas de eBay ya no corren con Celery (worker/beat/Redis eliminados).
# Ahora las dispara el servicio Railway Cron — ver railway.cron.toml.
cron: python manage.py correr_tareas_programadas
