from apps.support.models import Client


def calculate_client_total_price(client):
    return sum(cs.service.price for cs in client.clientservice_set.all())


def calculate_client_importance_multiplier(client, min_coef=1.02, max_coef=1.50):
    client_total = calculate_client_total_price(client)

    all_totals = [calculate_client_total_price(c) for c in Client.objects.all()]

    if not all_totals or all(t == 0 for t in all_totals):
        return min_coef

    all_totals.sort()
    rank = all_totals.index(client_total)

    p = 1.0 if len(all_totals) == 1 else rank / (len(all_totals) - 1)
    coef = min_coef + p * (max_coef - min_coef)
    return round(coef, 4)


SERVICE_TYPE_MULTIPLIERS = {
    "networks":      1.40,
    "it_services":   1.25,
    "external_calls":1.10,
    "local_phone":   1.01,
    "ip_tv":         1.05,
}


def calculate_final_priority(initial_priority: int, client: Client) -> int:

    priority = float(initial_priority)

    importance_multiplier = calculate_client_importance_multiplier(client)
    priority *= importance_multiplier

    if client.is_company:
        priority *= 1.30

    services = client.clientservice_set.all()

    services_multiplier = 1.0
    for cs in services:
        stype = cs.service.service_type
        mult = SERVICE_TYPE_MULTIPLIERS.get(stype)
        if mult:
            services_multiplier *= mult

    priority *= services_multiplier

    n = len(services)
    count_bonus = 1.0 + min(0.03 * n, 0.25)
    priority *= count_bonus

    priority = max(0.0, min(priority, 100.0))

    return int(round(priority))
