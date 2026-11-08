"""
Fill the database with demo data: divisions, categories, 23 places in Bangladesh,
tour packages, demo users, reviews and orders.

Run:  python manage.py seed_data
Running it again is safe, nothing is duplicated.
"""
import random
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from booking.models import Order, TourPackage
from booking.services import place_order
from tour.models import Category, Division, Review, TourDestination, Wishlist

# Cover pictures (most of them come from the first Pack-Go project)
COVER_PHOTOS = {
    "Cox's Bazar Sea Beach": 'coxs-bazar.jpg',
    'Sajek Valley': 'sajek.jpg',
    'Nilgiri, Bandarban': 'bandarban.jpg',
    'Rangamati & Kaptai Lake': 'rangamati.jpg',
    'Sundarbans': 'sundarbans.jpg',
    'Srimangal': 'sylhet-tea.jpg',
    "Saint Martin's Island": 'saint-martin.jpg',
    'Paharpur Buddhist Vihara': 'paharpur.jpg',
}

DIVISIONS = [
    ('Barishal', 'বরিশাল'), ('Chattogram', 'চট্টগ্রাম'), ('Dhaka', 'ঢাকা'), ('Khulna', 'খুলনা'),
    ('Mymensingh', 'ময়মনসিংহ'), ('Rajshahi', 'রাজশাহী'), ('Rangpur', 'রংপুর'), ('Sylhet', 'সিলেট'),
]

CATEGORIES = [
    ('Beach', 'water', 'Sea beaches and coastline'),
    ('Hills & Mountains', 'triangle', 'Hill tracts, peaks and valleys'),
    ('Forest & Wildlife', 'tree', 'Forests, national parks and wildlife'),
    ('Heritage & History', 'bank', 'Archaeological sites, forts, palaces and mosques'),
    ('Rivers & Wetlands', 'droplet', 'Rivers, haors, lakes and wetlands'),
    ('Tea Gardens', 'flower1', 'Tea estates and green countryside'),
    ('Island', 'sun', 'Islands in the Bay of Bengal'),
]

# name, division, district, category, lat, lng, best months, daily cost, featured, tagline,
# description, highlights, tips
DESTINATIONS = [
    ("Cox's Bazar Sea Beach", 'Chattogram', "Cox's Bazar", 'Beach', 21.4272, 92.0058, '11,12,1,2,3', 3500, True,
     'The longest natural sea beach in the world',
     "Cox's Bazar stretches for about 120 km along the Bay of Bengal and is Bangladesh's most popular holiday "
     "destination. Visitors come for wide sandy beaches, sunsets over the sea, fresh seafood and the scenic "
     "Marine Drive road towards Teknaf.",
     "Sunset at Laboni and Sugandha beach\nMarine Drive to Inani beach\nHimchari waterfall and hills\nBurmese market for local crafts",
     "Swim only in marked areas and follow lifeguard flags\nBook hotels early for December and January\nTry fresh seafood but confirm prices first"),
    ("Saint Martin's Island", 'Chattogram', "Cox's Bazar", 'Island', 20.6270, 92.3230, '11,12,1', 4000, True,
     'The only coral island of Bangladesh',
     "A small island in the north-eastern Bay of Bengal, about 9 km south of the Teknaf peninsula. Known for "
     "clear blue water, coral stones, coconut trees and a fragile marine ecosystem. Visitor access is regulated "
     "by the government to protect the island's environment.",
     "Coral-stone beaches\nCheradwip at low tide\nNight sky away from city lights",
     "Check the latest government rules on visiting season and visitor limits before planning\nDo not collect corals or shells\nCarry your waste back to the mainland"),
    ('Sajek Valley', 'Chattogram', 'Rangamati', 'Hills & Mountains', 23.3820, 92.2938, '6,7,8,9,10,11', 3500, True,
     'Walk above the clouds in the Chittagong Hill Tracts',
     'Sajek is a hilltop valley in Rangamati district, usually reached by jeep from Khagrachari. It is famous for '
     'sunrise views over a sea of clouds, especially in the rainy and autumn seasons, and for the culture of the '
     'indigenous communities who live there.',
     'Sunrise over the clouds at Konglak Para\nHelipad viewpoint at sunset\nLocal bamboo chicken and indigenous cuisine',
     'Jeeps leave Khagrachari in convoy with security escort at fixed times\nRespect local communities and ask before taking photos\nCarry cash; mobile network can be weak'),
    ('Nilgiri, Bandarban', 'Chattogram', 'Bandarban', 'Hills & Mountains', 21.9097, 92.3290, '10,11,12,1,2', 3000, False,
     'One of the highest tourist spots in the hill tracts',
     'Nilgiri is a hilltop resort area in Bandarban district with sweeping views of green hills and clouds. '
     'Bandarban is also home to Boga Lake, Nilachal, Golden Temple and many hiking trails.',
     'Cloud-covered hills in the morning\nNilachal and the Golden Temple\nTrekking routes towards Boga Lake',
     'Some areas need permission or a registered guide; follow local administration rules\nRoads are steep, avoid travelling after dark'),
    ('Rangamati & Kaptai Lake', 'Chattogram', 'Rangamati', 'Rivers & Wetlands', 22.6533, 92.1750, '9,10,11,12,1,2', 2800, False,
     'Boat rides on the largest man-made lake of Bangladesh',
     'Kaptai Lake was created by the Kaptai dam on the Karnaphuli river. Rangamati town sits on its shores, with '
     'boat trips to hanging bridges, island restaurants, Buddhist temples and indigenous handloom markets.',
     'The Rangamati hanging bridge\nBoat trip to Shuvolong waterfall\nRajban Vihara Buddhist temple',
     'Hire boats from authorised ghats and agree on the price first\nWaterfalls are fullest after the monsoon'),
    ('Nijhum Dwip', 'Chattogram', 'Noakhali', 'Island', 22.0500, 91.0000, '11,12,1,2', 2500, False,
     'A quiet island famous for spotted deer',
     'Nijhum Dwip is an island in the Hatiya area of Noakhali, protected as a national park. Its mangrove forest '
     'is home to spotted deer and many migratory birds in winter.',
     'Spotted deer in the forest at dawn\nMigratory birds in winter\nSunset over the Meghna estuary',
     'Travel time is long (launch to Hatiya, then local transport)\nAccommodation is basic; book in advance'),
    ('Sundarbans', 'Khulna', 'Khulna', 'Forest & Wildlife', 21.9497, 89.1833, '11,12,1,2', 5000, True,
     'The largest mangrove forest in the world',
     'The Sundarbans, a UNESCO World Heritage Site, spreads across the delta of the Ganges, Brahmaputra and '
     'Meghna rivers. It is the home of the Royal Bengal Tiger, spotted deer, crocodiles and hundreds of bird '
     'species. Most visitors explore it on guided multi-day boat trips from Khulna or Mongla.',
     'Boat safari through tidal creeks\nKatka and Kochikhali wildlife areas\nKaramjal wildlife centre',
     'Visit only with licensed tour operators and forest department permission\nFollow the guide; never walk alone in the forest\nCarry mosquito repellent and a power bank'),
    ('Sixty Dome Mosque, Bagerhat', 'Khulna', 'Bagerhat', 'Heritage & History', 22.6747, 89.7419, '10,11,12,1,2,3', 1800, False,
     'A 15th-century mosque in the UNESCO-listed Mosque City of Bagerhat',
     'Built in the 15th century by Khan Jahan Ali, the Shat Gombuj Masjid is one of the largest historic mosques '
     'in Bangladesh. Together with nearby monuments it forms the Historic Mosque City of Bagerhat, a UNESCO World '
     'Heritage Site.',
     'The many-domed prayer hall\nKhan Jahan Ali tomb and pond\nBagerhat museum',
     'Dress modestly and remove shoes inside the mosque\nAvoid visiting during prayer times'),
    ('Kuakata Sea Beach', 'Barishal', 'Patuakhali', 'Beach', 21.8167, 90.1200, '10,11,12,1,2', 2500, False,
     'Watch both sunrise and sunset from the same beach',
     'Kuakata is a long sea beach on the southern tip of Patuakhali district. It is one of the few places where '
     'both the sunrise and the sunset can be seen over the sea. Nearby are Rakhine villages, a Buddhist temple and '
     'fishing communities.',
     'Sunrise at Gangamati and sunset at the main beach\nRakhine village and Buddhist temple\nFresh fish market',
     'Motorbike rides along the beach are common; agree on price beforehand\nThe Padma Bridge has made the trip from Dhaka much shorter'),
    ('Floating Guava Market, Bhimruli', 'Barishal', 'Jhalokati', 'Rivers & Wetlands', 22.6000, 90.1300, '7,8,9', 2000, False,
     'Boats full of guavas on the backwaters of Barishal',
     'In the guava season, farmers from the surrounding orchards bring their harvest by small boats to Bhimruli '
     'canal, creating a colourful floating market. The region is known as the "Venice of Bengal" for its rivers.',
     'Floating market in the morning\nBoat rides through guava orchards\nRiver views of Barishal',
     'Go early in the morning when trading is busiest\nThe market runs mainly in July and August'),
    ('Ratargul Swamp Forest', 'Sylhet', 'Sylhet', 'Forest & Wildlife', 25.0083, 91.9575, '6,7,8,9,10', 2500, False,
     'The freshwater swamp forest of Sylhet',
     'Ratargul is a freshwater swamp forest in Gowainghat, Sylhet. During the rainy season the trees stand in '
     'water and visitors explore the forest by small wooden boats.',
     'Boat ride between submerged trees\nWatch tower view of the forest\nBirds and reptiles of the swamp',
     'Best when water is high (monsoon)\nWear a life jacket and do not litter in the water'),
    ('Jaflong', 'Sylhet', 'Sylhet', 'Rivers & Wetlands', 25.1630, 92.0175, '6,7,8,9,10,11', 2500, False,
     'Clear river water and stones at the foot of the Khasi hills',
     'Jaflong lies on the Piyain river near the India border. Visitors enjoy the view of hills across the border, '
     'clear river water flowing over stones, and the nearby tea gardens and Khasi villages.',
     'Piyain river and stone beds\nView of the Dawki bridge and hills\nKhasi village and tea garden',
     'Do not cross into the border area\nThe river current can be strong in the monsoon'),
    ('Srimangal', 'Sylhet', 'Moulvibazar', 'Tea Gardens', 24.3065, 91.7296, '6,7,8,9,10,11,12', 2500, True,
     'The tea capital of Bangladesh',
     'Srimangal is surrounded by rolling tea estates, pineapple and lemon gardens. Lawachara National Park, a '
     'tropical forest home to the western hoolock gibbon, is close by. It is famous for the multi-layer "seven '
     'colour" tea.',
     'Walk through green tea estates\nLawachara National Park trails\nSeven-layer tea',
     'Use a local guide inside Lawachara\nThe train from Dhaka is a comfortable, scenic option'),
    ('Tanguar Haor', 'Sylhet', 'Sunamganj', 'Rivers & Wetlands', 25.1500, 91.0800, '6,7,8,9,12,1', 4000, False,
     'A Ramsar wetland of open water and migratory birds',
     'Tanguar Haor in Sunamganj is a vast seasonal wetland and a Ramsar site. In the monsoon it becomes an inland '
     'sea where visitors stay on houseboats; in winter it hosts large flocks of migratory birds.',
     'Overnight stay on a houseboat\nSwimming tower and Niladri lake nearby\nMigratory birds in winter',
     'Choose houseboats with life jackets for everyone\nDo not use loud speakers or leave plastic in the haor'),
    ('Lalbagh Fort', 'Dhaka', 'Dhaka', 'Heritage & History', 23.7189, 90.3882, '10,11,12,1,2,3', 2500, False,
     'An unfinished 17th-century Mughal fort in Old Dhaka',
     'Construction of Lalbagh Fort began in 1678 under Mughal prince Muhammad Azam and was continued by Shaista '
     'Khan. The complex includes the tomb of Pari Bibi, a mosque and the Diwan-i-Aam with a museum.',
     'Tomb of Pari Bibi\nMughal gardens and fountains\nMuseum in the Diwan-i-Aam',
     'Check weekly closing days before visiting\nCombine with a food walk in Old Dhaka'),
    ('Ahsan Manzil', 'Dhaka', 'Dhaka', 'Heritage & History', 23.7086, 90.4060, '10,11,12,1,2,3', 2500, False,
     'The Pink Palace of the Nawabs of Dhaka',
     'Ahsan Manzil on the bank of the Buriganga was the residence of the Nawab family of Dhaka. Today it is a '
     'museum showing the palace rooms, furniture and the history of Dhaka.',
     'Pink palace façade by the Buriganga\nRestored durbar hall\nBoat view of Sadarghat',
     'Check opening days before visiting\nPhotography rules inside the museum may apply'),
    ('Panam City, Sonargaon', 'Dhaka', 'Narayanganj', 'Heritage & History', 23.6495, 90.6000, '10,11,12,1,2,3', 1800, False,
     'A street of abandoned merchant houses in the old capital of Bengal',
     'Sonargaon was an important capital and trade centre of medieval Bengal. Panam Nagar is a street lined with '
     'colonial-era merchant houses. Nearby is the Folk Arts and Crafts Museum.',
     'Panam Nagar heritage street\nFolk Arts and Crafts Museum\nGoaldi mosque',
     'Easy day trip from Dhaka\nDo not climb on fragile old buildings'),
    ('Paharpur Buddhist Vihara', 'Rajshahi', 'Naogaon', 'Heritage & History', 25.0310, 88.9770, '10,11,12,1,2,3', 1800, True,
     'Ruins of the great Somapura Mahavihara, a UNESCO World Heritage Site',
     'Somapura Mahavihara at Paharpur was one of the largest Buddhist monasteries south of the Himalayas, built in '
     'the 8th century during the Pala dynasty. Its terracotta plaques and huge central temple make it one of the '
     'most important archaeological sites in South Asia.',
     'Central temple mound\nTerracotta plaques\nSite museum',
     'Hire a guide to understand the history\nCarry water and a hat; there is little shade'),
    ('Mahasthangarh', 'Rajshahi', 'Bogura', 'Heritage & History', 24.9600, 89.3450, '10,11,12,1,2,3', 1800, False,
     'The ancient city of Pundranagara',
     'Mahasthangarh is among the earliest urban archaeological sites in Bangladesh, the remains of the ancient city '
     'of Pundranagara. The site includes city walls, mounds and a museum with finds from many periods.',
     'Ancient citadel walls\nGovinda Bhita and Behular Basor Ghar\nSite museum',
     'Bogura is famous for its yoghurt (doi); try it in town'),
    ('Kantajew Temple', 'Rangpur', 'Dinajpur', 'Heritage & History', 25.7930, 88.6680, '10,11,12,1,2,3', 1600, False,
     'An 18th-century temple covered in terracotta art',
     'Kantajew Temple (Kantanagar) near Dinajpur was completed in the 18th century. Every wall is covered with '
     'terracotta tiles that show scenes from epics and everyday life, making it one of the finest examples of '
     'terracotta architecture in Bangladesh.',
     'Terracotta panels on all walls\nRural Dinajpur countryside\nRamsagar lake nearby',
     'It is an active place of worship; behave respectfully'),
    ('Tajhat Palace', 'Rangpur', 'Rangpur', 'Heritage & History', 25.7200, 89.2700, '10,11,12,1,2,3', 1600, False,
     'A zamindar palace that is now the Rangpur museum',
     'Tajhat Palace was built in the early 20th century by a local zamindar. The white palace with its grand '
     'staircase now houses a museum of the Rangpur region.',
     'Grand marble staircase\nMuseum galleries\nPalace gardens',
     'Check opening days before visiting'),
    ('Birishiri & Bijoypur', 'Mymensingh', 'Netrokona', 'Rivers & Wetlands', 25.1300, 90.6400, '11,12,1,2,3', 2000, False,
     'Blue-green china clay lakes and the Someshwari river',
     'Birishiri in Durgapur upazila is known for the Someshwari river, the china clay hills of Bijoypur with their '
     'blue-green lakes, and the culture of the Garo and Hajong communities.',
     'China clay hills and lakes\nSomeshwari river\nCultural academy of local communities',
     'Roads can be rough; start early\nRespect local communities and their customs'),
    ('Shashi Lodge', 'Mymensingh', 'Mymensingh', 'Heritage & History', 24.7550, 90.4050, '10,11,12,1,2,3', 1600, False,
     'An early 20th-century zamindar palace in Mymensingh town',
     'Shashi Lodge, also known as the Mymensingh Rajbari, is a zamindar palace with a garden and a classical '
     'marble fountain. It is close to the Brahmaputra river walk in Mymensingh town.',
     'Palace building and fountain garden\nWalk along the old Brahmaputra\nZainul Abedin museum nearby',
     'Access to some parts of the building may be restricted'),
]

PACKAGES = [
    ("Cox's Bazar Beach Escape", ["Cox's Bazar Sea Beach"], 'BUS', 3, 8500, 30, 10,
     'Three relaxed days by the sea with a Marine Drive tour.',
     'Travel overnight from Dhaka by AC bus, enjoy two days on the beach, visit Inani and Himchari along the '
     'Marine Drive, and return on the third night.',
     'AC bus Dhaka - Cox\'s Bazar - Dhaka\n2 nights in a sea-view hotel (twin sharing)\nBreakfast and dinner\nMarine Drive sightseeing',
     'Lunch\nPersonal expenses'),
    ('Sundarbans Mangrove Expedition', ['Sundarbans'], 'BUS', 3, 12500, 24, 20,
     'A guided boat safari into the world\'s largest mangrove forest.',
     'Board a licensed tourist vessel at Khulna and spend three days exploring tidal creeks, forest trails and '
     'wildlife areas with an armed forest guard and an experienced guide.',
     'AC bus Dhaka - Khulna - Dhaka\nAll meals on the boat\nForest permission and guard\nCabin accommodation',
     'Personal expenses\nCamera fees if applicable'),
    ('Sylhet Tea & Swamp Tour', ['Srimangal', 'Ratargul Swamp Forest', 'Jaflong'], 'TRAIN', 4, 9800, 30, 15,
     'Tea gardens, a swamp forest and the Piyain river in one trip.',
     'Take the train to Srimangal for the tea estates and Lawachara, then continue to Sylhet for a boat ride in '
     'Ratargul and a day at Jaflong.',
     'Train tickets (AC chair)\n3 nights hotel (twin sharing)\nAll local transport\nBoat fare at Ratargul',
     'Meals not mentioned\nPersonal expenses'),
    ('Sajek Valley Cloud Trip', ['Sajek Valley'], 'BUS', 3, 7500, 25, 12,
     'Stay in a hilltop cottage and watch the sunrise above the clouds.',
     'Overnight bus to Khagrachari, jeep ride to Sajek, two nights in a cottage, and the famous Konglak Para '
     'sunrise walk.',
     'AC bus Dhaka - Khagrachari - Dhaka\nShared jeep to Sajek\n2 nights cottage\nAll meals in Sajek',
     'Personal expenses'),
    ('Heritage Trail of North Bengal', ['Paharpur Buddhist Vihara', 'Mahasthangarh', 'Kantajew Temple'], 'BUS', 4, 8900, 20, 25,
     'Ancient monasteries, cities and terracotta temples of North Bengal.',
     'A history-focused tour with a guide: the ruins of Mahasthangarh, the Somapura Mahavihara at Paharpur and '
     'the terracotta Kantajew Temple near Dinajpur.',
     'AC bus throughout\n3 nights hotel (twin sharing)\nHeritage guide\nEntry tickets',
     'Lunch\nPersonal expenses'),
    ("Saint Martin's Coral Island Getaway", ["Cox's Bazar Sea Beach", "Saint Martin's Island"], 'AIR', 4, 18500, 20, 30,
     "Fly to Cox's Bazar and sail to the coral island.",
     "Flight to Cox's Bazar, a day on the beach, then a ship to Saint Martin's Island subject to the government's "
     "visitor rules for the season.",
     "Return flight Dhaka - Cox's Bazar\nShip tickets\n3 nights accommodation\nBreakfast",
     'Lunch and dinner\nPersonal expenses'),
]

TRAVELERS = [
    ('ekram', 'Ekram', 'Shawon', 'Dhaka'), ('nabila', 'Nabila', 'Ashek', 'Dhaka'),
    ('faiza', 'Faiza', 'Zaman', 'Chattogram'), ('jannatul', 'Jannatul', 'Rikta', 'Sylhet'),
    ('mahmud', 'Mahmud', 'Shaheen', 'Rajshahi'), ('sadia', 'Sadia', 'Ahmed', 'Khulna'),
]
PASSWORD = 'Traveler@2026'

REVIEW_TEXTS = [
    (5, 'Absolutely beautiful', 'One of the best trips I have had in Bangladesh. Clean, peaceful and worth every taka.'),
    (4, 'Great experience', 'Lovely place and friendly local people. Roads were a bit rough but the view made up for it.'),
    (5, 'Must visit', 'Go in the right season and you will not regret it. Our guide explained everything well.'),
    (4, 'Worth the journey', 'Long travel time, but the place is stunning. Book accommodation early.'),
    (3, 'Good but crowded', 'Nice place, but it was very crowded during the holidays. Go on weekdays if you can.'),
]



class Command(BaseCommand):
    help = 'Load demo places, tour packages, users, reviews and orders.'

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(7)
        divisions = {}
        for name, bangla in DIVISIONS:
            divisions[name], _ = Division.objects.update_or_create(name=name, defaults={'bangla_name': bangla})
        categories = {}
        for name, icon, _ in CATEGORIES:
            categories[name], _ = Category.objects.update_or_create(name=name, defaults={'icon': icon})

        places = {}
        photo_dir = Path(settings.BASE_DIR) / 'static' / 'images' / 'destinations'
        for (name, division, district, category, lat, lng, months, cost, featured,
             short, description, highlights, tips) in DESTINATIONS:
            place, _ = TourDestination.objects.update_or_create(name=name, defaults={
                'division': divisions[division], 'district': district, 'category': categories[category],
                'latitude': lat, 'longitude': lng, 'best_months': months, 'price_per_day': cost,
                'is_featured': featured, 'short_description': short, 'description': description,
                'highlights': highlights, 'tips': tips,
            })
            photo = COVER_PHOTOS.get(name)
            if photo and not place.cover_image and (photo_dir / photo).exists():
                with open(photo_dir / photo, 'rb') as f:
                    place.cover_image.save(photo, File(f), save=True)
            places[name] = place
        self.stdout.write(f'  {len(places)} places in {len(divisions)} divisions')

        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@tourvibe.test', 'Admin@12345')
            admin.profile.full_name = 'Admin'
            admin.profile.save()

        travelers = []
        for username, first, last, city in TRAVELERS:
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User.objects.create_user(username, f'{username}@tourvibe.test', PASSWORD,
                                                first_name=first, last_name=last)
                user.profile.full_name = f'{first} {last}'
                user.profile.home_city = city
                user.profile.phone_number = '01712345678'
                user.profile.save()
            travelers.append(user)

        today = timezone.localdate()
        packages = []
        for (title, place_names, transport, days, price, seats, start_in, summary, description, includes,
             excludes) in PACKAGES:
            package, created = TourPackage.objects.get_or_create(title=title, defaults={
                'transport': transport, 'days': days, 'price_per_person': price, 'total_seats': seats,
                'start_date': today + timedelta(days=start_in), 'summary': summary, 'description': description,
                'includes': includes, 'excludes': excludes,
            })
            if not created and package.start_date <= today:
                package.start_date = today + timedelta(days=start_in)
                package.save(update_fields=['start_date'])
            package.destinations.set([places[n] for n in place_names])
            packages.append(package)

        if not Review.objects.exists():
            for place in places.values():
                for user in random.sample(travelers, k=random.randint(1, 4)):
                    rating, title, comment = random.choice(REVIEW_TEXTS)
                    Review.objects.create(tour=place, user=user, rating=rating, title=title, comment=comment,
                                          visited_on=today - timedelta(days=random.randint(20, 400)))

        if not Wishlist.objects.exists():
            for user in travelers:
                for place in random.sample(list(places.values()), k=3):
                    Wishlist.objects.get_or_create(user=user, tour=place)

        if not Order.objects.exists():
            statuses = [Order.CONFIRMED] * 6 + [Order.PENDING] * 3 + [Order.CANCELLED]
            for i in range(16):
                user = travelers[i % len(travelers)]
                picked = random.sample(packages, k=random.choice([1, 1, 2]))
                order = place_order(user, [(p, random.randint(1, 3)) for p in picked],
                                    user.profile.display_name, '01712345678')
                # Spread orders over the last 5 months so the dashboard charts have history
                Order.objects.filter(pk=order.pk).update(
                    status=random.choice(statuses),
                    created_at=timezone.now() - timedelta(days=random.randint(0, 150)))

        self.stdout.write(self.style.SUCCESS('Demo data is ready.'))
        self.stdout.write('  Admin:     admin / Admin@12345')
        self.stdout.write(f'  Travelers: ekram, nabila, faiza, jannatul, mahmud, sadia / {PASSWORD}')
