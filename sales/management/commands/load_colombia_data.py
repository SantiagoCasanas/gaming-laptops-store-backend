from django.core.management.base import BaseCommand
from sales.models import Departamento, Ciudad


class Command(BaseCommand):
    help = 'Load Colombian departments and cities'

    def handle(self, *args, **options):
        data = {
            'Amazonas': ['Leticia', 'Puerto Nariño'],
            'Antioquia': ['Medellín', 'Aburrá', 'Bello', 'Envigado', 'Itagüí', 'La Ceja', 'Rionegro'],
            'Arauca': ['Arauca', 'Fortul', 'Saravena'],
            'Atlántico': ['Barranquilla', 'Soledad', 'Malambo', 'Puerto Colombia'],
            'Bolívar': ['Cartagena', 'Magangué', 'Santa Cartagena'],
            'Boyacá': ['Tunja', 'Duitama', 'Sogamoso', 'Paipa', 'Tundama'],
            'Caldas': ['Manizales', 'Villamaría', 'Chinchiná', 'La Dorada'],
            'Caquetá': ['Florencia', 'San Vicente del Caguán'],
            'Cauca': ['Popayán', 'Santander de Quilichao', 'Puerto Tejada'],
            'Cesar': ['Valledupar', 'Aguachica', 'Bosconia'],
            'Chocó': ['Quibdó', 'Istmina', 'Condoto'],
            'Córdoba': ['Montería', 'Cereté', 'Lorica'],
            'Cundinamarca': ['Bogotá', 'Soacha', 'Facatativá', 'Fusagasugá', 'Zipaquirá', 'Chia', 'Mosquera', 'Madrid', 'Ubaté'],
            'Guainía': ['Puerto Inírida', 'San Felipe'],
            'Guaviare': ['San José del Guaviare', 'Calamar'],
            'Huila': ['Neiva', 'La Plata', 'Pitalito', 'Garzón'],
            'La Guajira': ['Riohacha', 'Maicao', 'Uribia'],
            'Magdalena': ['Santa Marta', 'Ciénaga', 'Fundación'],
            'Meta': ['Villavicencio', 'Granada', 'Acacías', 'Puerto López'],
            'Nariño': ['Pasto', 'Ipiales', 'Tumaco', 'Puerto Asís'],
            'Norte de Santander': ['Cúcuta', 'Bucaramanga', 'Pamplona', 'Ocaña'],
            'Putumayo': ['Mocoa', 'Puerto Caicedo', 'Sibundoy'],
            'Quindío': ['Armenia', 'Pereira', 'Dosquebradas'],
            'Risaralda': ['Pereira', 'Dosquebradas', 'Santa Rosa'],
            'Santander': ['Bucaramanga', 'Floridablanca', 'Girón', 'Piedecuesta', 'Barrancabermeja'],
            'Sucre': ['Sincelejo', 'Corozal', 'Sampués'],
            'Tolima': ['Ibagué', 'Espinal', 'Líbano'],
            'Valle del Cauca': ['Cali', 'Palmira', 'Buenaventura', 'Cartago', 'Tuluá'],
            'Vaupés': ['Mitú', 'Carurú'],
            'Vichada': ['Puerto Carreño', 'Santa Rosalía'],
        }

        count_depts = 0
        count_cities = 0

        for dept_name, cities in data.items():
            # Create or get department
            dept, created = Departamento.objects.get_or_create(nombre=dept_name)
            if created:
                count_depts += 1
                self.stdout.write(self.style.SUCCESS(f'Created department: {dept_name}'))

            # Create cities
            for city_name in cities:
                city, created = Ciudad.objects.get_or_create(
                    nombre=city_name,
                    departamento=dept
                )
                if created:
                    count_cities += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully loaded {count_depts} departments and {count_cities} cities'
            )
        )
