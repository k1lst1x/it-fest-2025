import random
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.support.models import (
    Client,
    Service,
    ClientService,
    Engineer,
    SupportTicket,
)

LAST_NAMES = [
    "Куанышбеков", "Арыстанов", "Бектуров", "Жанабаев", "Кожахмет",
    "Серикжанов", "Тайманов", "Утегенов", "Баймуханов", "Кенжетаев",
    "Орлов", "Герасимов", "Ковалев", "Рожков", "Лебедев"
]

FIRST_NAMES = [
    "Нурсултан", "Арман", "Лейла", "Асель", "Рахим", "Жанара",
    "Гульмира", "Данияр", "Мирлан", "Назгуль", "Оскар", "Валерия",
    "Рустам", "Полина", "Илья"
]

STREETS = [
    "Казыбек би", "Улы Дала", "Жансугурова", "Мустафы Шокая", "Тургут Озала",
    "Шарипова", "Кошкарбаева", "Махамбета", "Казыгурт", "Шаймерденова",
    "Победы", "Комсомольская", "Университетская", "Пролетарская"
]

COMPANY_PREFIXES = ["LLP", "LLC", "ТОО", "ФОП"]
KAZAKH_COMPANY_WORDS = [
    "Samruk", "Zaman", "NurTrade", "Sapar", "Orda", "Sunkar", "Koktem", "Zhol"
]

SCENARIOS = {
    "networks": [
        {
            "desc": "Частые всплески пинга на игровых серверах",
            "eng": "Проверка наличия джиттера и пиков в очередях на маршрутизаторе, QoS профилизация.",
            "client": "Отключите все фоновые обновления и приложения, проверьте проводное подключение.",
            "fix": "Настроены QoS и полоса пропускания; джиттер снизился до приемлемого уровня.",
            "prob": 35,
            "visit": 5
        },
        {
            "desc": "Полная потеря доступа после грозы",
            "eng": "Осмотр уличного распределительного шкафчика: повреждена муфта, вода в кабеле.",
            "client": "Отключите внутреннее сетевое оборудование до приезда инженера.",
            "fix": "Заменена повреждённая муфта, восстановлена непрерывность волокна.",
            "prob": 45,
            "visit": 95
        },
        {
            "desc": "Снижение скорости в вечерние часы",
            "eng": "Проверка пиков нагрузки на аггрегирующих узлах и лимитов тарифа.",
            "client": "Попробуйте перезагрузить домашний роутер ночью, протестируйте в 03:00.",
            "fix": "Провайдер увеличил пулы на узлах, пик смещён — скорость стабилизирована.",
            "prob": 20,
            "visit": 10
        },
    ],
    "ip_tv": [
        {
            "desc": "Задержка аудио относительно видео",
            "eng": "Проверка декодеров и буферизации на STB, синхронизация потоков.",
            "client": "Перезагрузите приставку, проверьте настройки аудиовыхода телевизора.",
            "fix": "Обновлена прошивка приставки, аудио синхронизировано.",
            "prob": 30,
            "visit": 40
        },
        {
            "desc": "Отсутствуют премиальные каналы",
            "eng": "Проверка подписок по аккаунту абонента в биллинге и ACL на CDN.",
            "client": "Проверьте статус подписки в личном кабинете.",
            "fix": "Восстановлена подписка через биллинг, каналы доступны.",
            "prob": 50,
            "visit": 0
        },
    ],
    "local_phone": [
        {
            "desc": "Короткие обрывы разговора каждые 10 минут",
            "eng": "Анализ качества линии и обнаружение интерференции, проверка кроссов.",
            "client": "Попробуйте другой аппарат и другой телефонный кабель.",
            "fix": "Выявлено пробитие в кабеле в подъезде, выполнена замена линии.",
            "prob": 60,
            "visit": 80
        }
    ],
    "it_services": [
        {
            "desc": "Доступ к корпоративной почте невозможен",
            "eng": "Проверка MX записей, сертификатов и доступности SMTP/IMAP сервисов.",
            "client": "Попробуйте открыть почту через веб-интерфейс с другого устройства.",
            "fix": "Перезапущены почтовые сервисы, восстановлены сертификаты.",
            "prob": 45,
            "visit": 20
        },
        {
            "desc": "Падение приватного облака (backup failed)",
            "eng": "Проверка дискового пространства, прав доступа и логов агента резервного копирования.",
            "client": "Убедитесь, что на сервере достаточно свободного места.",
            "fix": "Расширено хранилище, резервные задания успешно завершились.",
            "prob": 25,
            "visit": 30
        }
    ],
    "external_calls": [
        {
            "desc": "Проблемы с исходящей связью на SIP-каналах",
            "eng": "Проверка транков, авторизации у оператора и трансляции RTP.",
            "client": "Перезапустите софтфон или IP-АТС; проверьте настройки кодеков.",
            "fix": "Перенастроены транки, связь восстановлена.",
            "prob": 40,
            "visit": 10
        }
    ],
    "default": [
        {
            "desc": "Запрос на консультацию по тарифам и опциям",
            "eng": "Клиенту предоставлена информация по доступным пакетам и дополнительным услугам.",
            "client": "Ознакомьтесь с предложениями в личном кабинете или на сайте.",
            "fix": "Информация предоставлена, клиент удовлетворён.",
            "prob": 10,
            "visit": 0
        }
    ]
}

class Command(BaseCommand):
    help = "Генерация уникальных тестовых данных"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("\n=== СТАРТ ЗАПОЛНЕНИЯ НОВЫМИ ДАННЫМИ ===\n"))

        with transaction.atomic():
            self._delete_all()
            services = self._seed_services()
            engineers = self._seed_engineers()
            clients = self._seed_clients(count=60)
            self._seed_client_services(clients, services)
            self._seed_tickets(clients, engineers, count=300)

        self.stdout.write(self.style.SUCCESS("\n=== ГОТОВО: БАЗА ЗАПОЛНЕНА НОВЫМИ ДАННЫМИ ===\n"))

    def _delete_all(self):
        SupportTicket.objects.all().delete()
        ClientService.objects.all().delete()
        Engineer.objects.all().delete()
        Client.objects.all().delete()
        Service.objects.all().delete()

    def _seed_services(self):
        data = [
            ("Fiber Home 200 (200 Мбит)", "networks", 5200),
            ("Fiber Pro Gamer (800 Мбит)", "networks", 9500),
            ("Business Prime 2Gbps", "networks", 48000),
            ("VoIP Lite (городской)", "external_calls", 1800),
            ("EduTV Streaming (100 каналов)", "ip_tv", 1500),
            ("Cloud Backup 'SafeBox'", "it_services", 7200),
            ("Managed LAN Setup", "it_services", 8800),
            ("Smart Security Pack (IoT)", "it_services", 4300),
        ]
        return [Service.objects.create(title=t, service_type=s, price=p) for t, s, p in data]

    def _seed_engineers(self):
        names = [
            "Айбек Тлеубаев", "Мария Кузьмина", "Саят Орынбасаров", "Ольга Романовa",
            "Ерлан Бекмуханов", "Надежда Семёнова", "Бекзат Карасай", "Лилия Ахметова",
            "Мирель Даригерова", "Алексей Белов"
        ]
        engineers = []
        for n in names:
            active = random.random() > 0.15
            engineers.append(Engineer.objects.create(full_name=n, is_active=active))
        return engineers

    def _seed_clients(self, count):
        clients = []
        for i in range(count):
            is_company = random.random() < 0.18

            if is_company:
                word = random.choice(KAZAKH_COMPANY_WORDS)
                prefix = random.choice(COMPANY_PREFIXES)
                full_name = f'{prefix} "{word} Solutions {random.randint(100,999)}"'
                age = 0
            else:
                ln = random.choice(LAST_NAMES)
                fn = random.choice(FIRST_NAMES)
                patronymic = random.choice(FIRST_NAMES) + "қызы" if random.random() < 0.15 else ""
                full_name = f"{ln} {fn} {patronymic}".strip()
                age = random.randint(18, 75)

            phone_prefix = random.choice(['701', '702', '705', '777', '776', '747'])
            phone = f"+7{phone_prefix}{random.randint(2000000, 9999999)}"

            email = f"contact_{i}_{random.randint(100,999)}@samplecorp.kz"
            street = random.choice(STREETS)
            address_type = "офис" if is_company else "дом"
            address = f"г. Нур-Султан, ул. {street}, д. {random.randint(1,300)}, {address_type} {random.randint(1,50)}"

            client = Client.objects.create(
                full_name=full_name,
                email=email,
                phone_number=phone,
                service_address=address,
                age=age,
                is_company=is_company
            )
            clients.append(client)
        return clients

    def _seed_client_services(self, clients, services):
        for client in clients:
            num = random.randint(1, 4)
            pool = list(services)

            if client.is_company:
                business = [s for s in pool if "Business" in s.title or "Managed" in s.title or s.service_type == "it_services"]
                if business:
                    ClientService.objects.create(client=client, service=random.choice(business))
                    num = max(1, num - 1)

            remaining = [s for s in pool if not ClientService.objects.filter(client=client, service=s).exists()]
            for s in random.sample(remaining, min(len(remaining), num)):
                ClientService.objects.create(client=client, service=s)

    def _seed_tickets(self, clients, engineers, count):
        active = [e for e in engineers if e.is_active] or engineers

        end = timezone.now()
        start = end - datetime.timedelta(days=180)

        for _ in range(count):
            client = random.choice(clients)
            services = ClientService.objects.filter(client=client).select_related('service')
            if not services.exists():
                continue

            target = random.choice(services)
            s_type = target.service.service_type

            scenarios = SCENARIOS.get(s_type, SCENARIOS["default"])
            scenario = random.choices(scenarios, weights=[s['prob'] for s in scenarios], k=1)[0]

            rand_sec = random.randint(0, int((end - start).total_seconds()))
            created = start + datetime.timedelta(seconds=rand_sec)
            days = (end - created).days

            status = "new"
            closed = None
            final_res = None
            engineer = None

            if days > 30 and random.random() < 0.95:
                status = "done"
            elif days > 10 and random.random() < 0.8:
                status = "done"
            elif days > 2:
                status = random.choices(["in_progress", "done"], weights=[60, 40], k=1)[0]
            else:
                status = random.choices(["new", "in_progress"], weights=[55, 45], k=1)[0]

            if status in ("in_progress", "done"):
                engineer = random.choice(active)
                if status == "done":
                    duration = datetime.timedelta(hours=random.randint(2, 200))
                    closed = created + duration
                    options = [
                        "Работа выполнена по удалённой инструкции.",
                        "Инженер выезжал и устранил неисправность на месте.",
                        "Клиент подтвердил восстановление сервиса."
                    ]
                    final_res = f"{scenario['fix']} {random.choice(options)}"

            base = 40
            if client.is_company:
                base += 25
            if scenario.get("visit", 0) > 60:
                base += 18
            priority = min(100, max(5, base + random.randint(-20, 15)))

            why_needed = None
            if scenario.get("visit", 0) > 60 and status != "done":
                why_needed = f"Требуется выезд: {client.service_address}. Проблема: {scenario['desc']}"

            ticket = SupportTicket.objects.create(
                client=client,
                engineer=engineer,
                description=scenario["desc"],
                priority_score=priority,
                engineer_visit_probability=scenario.get("visit", 0),
                why_engineer_needed=why_needed,
                proposed_solution_engineer=scenario.get("eng"),
                proposed_solution_client=scenario.get("client"),
                final_resolution=final_res,
                status=status,
                closed_at=closed
            )

            SupportTicket.objects.filter(pk=ticket.pk).update(created_at=created)
