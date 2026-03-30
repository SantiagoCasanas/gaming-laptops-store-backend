from django.core.management.base import BaseCommand
from sales.models import Departamento, Ciudad


COLOMBIA_LOCATIONS = [
    {
        "nombre": "Amazonas", "codigo": "91",
        "ciudades": ["Leticia", "Puerto Nariño"]
    },
    {
        "nombre": "Antioquia", "codigo": "05",
        "ciudades": ["Medellín", "Bello", "Itagüí", "Envigado", "Rionegro", "Apartadó", "Turbo", "Caucasia", "Sabaneta", "Copacabana"]
    },
    {
        "nombre": "Arauca", "codigo": "81",
        "ciudades": ["Arauca", "Arauquita", "Saravena", "Tame"]
    },
    {
        "nombre": "Atlántico", "codigo": "08",
        "ciudades": ["Barranquilla", "Soledad", "Malambo", "Sabanalarga", "Baranoa"]
    },
    {
        "nombre": "Bolívar", "codigo": "13",
        "ciudades": ["Cartagena", "Magangué", "El Carmen de Bolívar", "Turbaco", "Mompox"]
    },
    {
        "nombre": "Boyacá", "codigo": "15",
        "ciudades": ["Tunja", "Duitama", "Sogamoso", "Chiquinquirá", "Paipa"]
    },
    {
        "nombre": "Caldas", "codigo": "17",
        "ciudades": ["Manizales", "La Dorada", "Riosucio", "Salamina", "Chinchiná"]
    },
    {
        "nombre": "Caquetá", "codigo": "18",
        "ciudades": ["Florencia", "San Vicente del Caguán", "La Montañita", "El Doncello"]
    },
    {
        "nombre": "Casanare", "codigo": "85",
        "ciudades": ["Yopal", "Aguazul", "Villanueva", "Paz de Ariporo", "Tauramena"]
    },
    {
        "nombre": "Cauca", "codigo": "19",
        "ciudades": ["Popayán", "Santander de Quilichao", "Puerto Tejada", "Piendamó", "El Tambo"]
    },
    {
        "nombre": "Cesar", "codigo": "20",
        "ciudades": ["Valledupar", "Aguachica", "Bosconia", "Codazzi", "La Jagua de Ibirico"]
    },
    {
        "nombre": "Chocó", "codigo": "27",
        "ciudades": ["Quibdó", "Istmina", "Riosucio", "Bahía Solano", "Nuquí"]
    },
    {
        "nombre": "Córdoba", "codigo": "23",
        "ciudades": ["Montería", "Cereté", "Lorica", "Sahagún", "Montelíbano"]
    },
    {
        "nombre": "Cundinamarca", "codigo": "25",
        "ciudades": ["Bogotá D.C.", "Soacha", "Facatativá", "Zipaquirá", "Fusagasugá", "Chía", "Mosquera", "Madrid", "Funza", "Cajicá"]
    },
    {
        "nombre": "Guainía", "codigo": "94",
        "ciudades": ["Inírida"]
    },
    {
        "nombre": "Guaviare", "codigo": "95",
        "ciudades": ["San José del Guaviare", "El Retorno", "Calamar"]
    },
    {
        "nombre": "Huila", "codigo": "41",
        "ciudades": ["Neiva", "Pitalito", "Garzón", "La Plata", "Campoalegre"]
    },
    {
        "nombre": "La Guajira", "codigo": "44",
        "ciudades": ["Riohacha", "Maicao", "Uribia", "Manaure", "Fonseca"]
    },
    {
        "nombre": "Magdalena", "codigo": "47",
        "ciudades": ["Santa Marta", "Ciénaga", "Fundación", "El Banco", "Plato"]
    },
    {
        "nombre": "Meta", "codigo": "50",
        "ciudades": ["Villavicencio", "Acacías", "Granada", "Puerto López", "San Martín"]
    },
    {
        "nombre": "Nariño", "codigo": "52",
        "ciudades": ["Pasto", "Tumaco", "Ipiales", "Túquerres", "La Unión"]
    },
    {
        "nombre": "Norte de Santander", "codigo": "54",
        "ciudades": ["Cúcuta", "Ocaña", "Pamplona", "Villa del Rosario", "Los Patios"]
    },
    {
        "nombre": "Putumayo", "codigo": "86",
        "ciudades": ["Mocoa", "Puerto Asís", "Orito", "Valle del Guamuez", "Sibundoy"]
    },
    {
        "nombre": "Quindío", "codigo": "63",
        "ciudades": ["Armenia", "Calarcá", "Montenegro", "La Tebaida", "Quimbaya"]
    },
    {
        "nombre": "Risaralda", "codigo": "66",
        "ciudades": ["Pereira", "Dosquebradas", "Santa Rosa de Cabal", "La Virginia", "Belén de Umbría"]
    },
    {
        "nombre": "San Andrés y Providencia", "codigo": "88",
        "ciudades": ["San Andrés", "Providencia"]
    },
    {
        "nombre": "Santander", "codigo": "68",
        "ciudades": ["Bucaramanga", "Floridablanca", "Girón", "Piedecuesta", "Barrancabermeja", "San Gil", "Socorro"]
    },
    {
        "nombre": "Sucre", "codigo": "70",
        "ciudades": ["Sincelejo", "Corozal", "San Marcos", "Tolú", "Sampués"]
    },
    {
        "nombre": "Tolima", "codigo": "73",
        "ciudades": ["Ibagué", "Espinal", "Melgar", "Honda", "Líbano"]
    },
    {
        "nombre": "Valle del Cauca", "codigo": "76",
        "ciudades": ["Cali", "Buenaventura", "Palmira", "Tuluá", "Buga", "Cartago", "Jamundí", "Yumbo", "Candelaria", "Buenaventura"]
    },
    {
        "nombre": "Vaupés", "codigo": "97",
        "ciudades": ["Mitú", "Carurú"]
    },
    {
        "nombre": "Vichada", "codigo": "99",
        "ciudades": ["Puerto Carreño", "La Primavera", "Santa Rosalía"]
    },
]


class Command(BaseCommand):
    help = 'Seed Colombian departments and cities from DIVIPOLA data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== SEEDING COLOMBIA LOCATIONS ===\n'))

        dept_created = 0
        dept_existing = 0
        city_created = 0
        city_existing = 0

        for dept_data in COLOMBIA_LOCATIONS:
            departamento, created = Departamento.objects.update_or_create(
                nombre=dept_data['nombre'],
                defaults={'codigo': dept_data['codigo']}
            )
            if created:
                dept_created += 1
                self.stdout.write(f'  [+] Departamento: {departamento.nombre}')
            else:
                dept_existing += 1

            for ciudad_nombre in dept_data['ciudades']:
                _, c_created = Ciudad.objects.update_or_create(
                    nombre=ciudad_nombre,
                    departamento=departamento,
                )
                if c_created:
                    city_created += 1
                else:
                    city_existing += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDepartamentos: {dept_created} nuevos, {dept_existing} existentes'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Ciudades: {city_created} nuevas, {city_existing} existentes'
        ))
        self.stdout.write(self.style.SUCCESS('\n=== SEED COMPLETADO ===\n'))
