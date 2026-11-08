"""
Trip planner engine.

estimate_trip()  -> full cost of a trip with several destinations
recommend()      -> ranks destinations for a month, budget and interests

These are plain Python functions, so the web pages, the REST API and the
tests all use the same logic. Money is in BDT. The rates are planning
assumptions and are shown to the user with every estimate.
"""
import math

from tour.models import DHAKA, MONTHS, distance_km

ROAD_FACTOR = 1.35            # roads are longer than a straight line
RATE_PER_KM = {'BUS': 2.0, 'TRAIN': 1.5, 'AIR': 7.5}   # per person
MIN_AIR_FARE = 4500           # per person, per flight
CAR_RATE_PER_KM = 28.0        # per car (fuel + driver)
CAR_SEATS = 4
BUDGET_LEVELS = {'BUDGET': 0.7, 'STANDARD': 1.0, 'PREMIUM': 1.8}
STAY_SHARE = 0.55             # part of the daily cost that is hotel
EXTRA = 0.10                  # 10% extra for local transport and surprises

ASSUMPTIONS = [
    'Road distance = 1.35 x straight-line (GPS) distance.',
    'Per person per km: AC bus ৳2.0, train ৳1.5, flight ৳7.5 (at least ৳4,500 per flight).',
    'Private car: ৳28 per km, one car for every 4 travelers.',
    'Food and hotel come from each place\'s usual daily cost: Budget 70%, Standard 100%, Premium 180%.',
    'Two travelers share one room.',
    '10% extra is added for local transport and surprises.',
    'These are estimates for planning, not live prices.',
]


class PlannerError(ValueError):
    pass


def best_route(places, start=DHAKA):
    """
    Put the places in a short travel order.

    Nearest-neighbour method (a simple solution for the Travelling Salesman
    Problem): from where you are, go to the closest place you have not visited,
    and at the end come back to the start. Returns (ordered places, km).
    """
    left = list(places)
    here = start
    route, km = [], 0.0
    while left:
        nxt = min(left, key=lambda p: distance_km(here[0], here[1], float(p.latitude), float(p.longitude)))
        km += distance_km(here[0], here[1], float(nxt.latitude), float(nxt.longitude))
        here = (float(nxt.latitude), float(nxt.longitude))
        route.append(nxt)
        left.remove(nxt)
    if route:
        km += distance_km(here[0], here[1], start[0], start[1])
    return route, km


def share_days(days, count):
    base, extra = divmod(days, count)
    return [base + (1 if i < extra else 0) for i in range(count)]


def transport_cost(road_km, trips, travelers, mode):
    if mode == 'CAR':
        return road_km * CAR_RATE_PER_KM * math.ceil(travelers / CAR_SEATS)
    if mode not in RATE_PER_KM:
        raise PlannerError(f'Unknown transport: {mode}')
    per_person = road_km * RATE_PER_KM[mode]
    if mode == 'AIR':
        per_person = max(per_person, MIN_AIR_FARE * trips)
    return per_person * travelers


def estimate_trip(places, days, travelers, budget='STANDARD', transport='BUS'):
    places = list(dict.fromkeys(places))
    try:
        days, travelers = int(days), int(travelers)
    except (TypeError, ValueError):
        raise PlannerError('Days and travelers must be numbers.')
    if not places:
        raise PlannerError('Choose at least one place.')
    if len(places) > 8:
        raise PlannerError('You can choose at most 8 places.')
    if not 1 <= days <= 30:
        raise PlannerError('Trip length must be 1 to 30 days.')
    if not 1 <= travelers <= 20:
        raise PlannerError('Travelers must be 1 to 20.')
    if days < len(places):
        raise PlannerError('Keep at least one day for each place.')
    if budget not in BUDGET_LEVELS:
        raise PlannerError(f'Unknown budget level: {budget}')

    route, km = best_route(places)
    road_km = km * ROAD_FACTOR
    day_plan = share_days(days, len(route))

    hotel = food = 0.0
    for place, n in zip(route, day_plan):
        daily = place.price_per_day * BUDGET_LEVELS[budget]
        hotel += daily * STAY_SHARE * n
        food += daily * (1 - STAY_SHARE) * n
    hotel *= math.ceil(travelers / 2)
    food *= travelers

    tickets = sum(p.entry_fee or 0 for p in route) * travelers
    travel = transport_cost(road_km, len(route) + 1, travelers, transport)
    subtotal = travel + hotel + food + tickets
    extra = subtotal * EXTRA
    total = round(subtotal + extra)

    return {
        'route': [{'name': p.name, 'slug': p.slug, 'district': p.district} for p in route],
        'distance_km': round(road_km),
        'days_at_each': {p.name: n for p, n in zip(route, day_plan)},
        'breakdown': {
            'transport': round(travel),
            'hotel': round(hotel),
            'food': round(food),
            'entry_fees': round(tickets),
            'extra': round(extra),
        },
        'total': total,
        'per_person': round(total / travelers),
        'days': days,
        'travelers': travelers,
        'assumptions': ASSUMPTIONS,
    }


# ---- Recommendation ----

WEIGHTS = {'season': 40, 'budget': 30, 'interest': 20, 'rating': 10}


def month_gap(a, b):
    gap = abs(a - b) % 12
    return min(gap, 12 - gap)


def score_place(place, month, daily_budget=None, categories=None, avg_rating=None):
    """Score out of 100 from four weighted parts. Also returns the reasons."""
    score, reasons = 0.0, []

    gap = min(month_gap(month, m) for m in place.month_list)
    if gap == 0:
        score += WEIGHTS['season']
        reasons.append(f'{MONTHS[month - 1]} is one of the best months to visit')
    elif gap == 1:
        score += WEIGHTS['season'] / 2
        reasons.append(f'Close to the best season ({place.month_names})')

    if daily_budget:
        ratio = place.price_per_day / float(daily_budget)
        if ratio <= 1:
            score += WEIGHTS['budget']
            reasons.append(f'Fits your budget (about ৳{place.price_per_day:,}/day)')
        elif ratio < 2:
            score += WEIGHTS['budget'] * (2 - ratio)
            reasons.append(f'A bit above your budget (about ৳{place.price_per_day:,}/day)')
    else:
        score += WEIGHTS['budget'] / 2

    if categories:
        if place.category_id in categories:
            score += WEIGHTS['interest']
            reasons.append(f'Matches your interest: {place.category.name}')
    else:
        score += WEIGHTS['interest'] / 2

    if avg_rating:
        score += WEIGHTS['rating'] * float(avg_rating) / 5
        if avg_rating >= 4:
            reasons.append(f'Travelers rate it {avg_rating:.1f}/5')
    else:
        score += WEIGHTS['rating'] / 2

    return round(score, 1), reasons


def recommend(places, month, daily_budget=None, categories=None, max_km=None, limit=6):
    if not 1 <= int(month) <= 12:
        raise PlannerError('Month must be 1 to 12.')
    categories = {int(c) for c in (categories or [])}
    results = []
    for place in places.select_related('category', 'division').with_rating():
        if max_km and place.km_from_dhaka > float(max_km):
            continue
        score, reasons = score_place(place, int(month), daily_budget, categories, place.avg_rating)
        results.append({'place': place, 'score': score, 'reasons': reasons})
    results.sort(key=lambda r: (-r['score'], r['place'].name))
    return results[:limit]
