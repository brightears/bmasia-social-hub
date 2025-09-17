#!/usr/bin/env python3
"""
Update venue_data.md with contact information from the table
"""

import re

# Contact data from the table
contacts_data = [
    {"venue": "AVANI+ Samui Resort", "name": "Anan Hayicheteh", "title": "Cluster Assistant IT Manager", "email": "anan_ha@minor.com"},
    {"venue": "Citadines Danube Vienna", "name": "Arnold Konrath", "title": "Residence Manager", "email": "arnold.konrath@citadines.com"},
    {"venue": "Veriu Group", "name": "Kyle Kaya", "title": "Director of Operations", "email": "kyle.kaya@veriugroup.com.au"},
    {"venue": "Swissôtel Bangkok Ratchada", "name": "Dejpasit Narkpraphan", "title": "IT Manager", "email": "dejpasit.narkpraphan@swissotel.com"},
    {"venue": "The Aberdeen Marina Club", "name": "Vanessa Wong", "title": "Administrative Manager - Operations & Quality", "email": "vanessaky.wong@aberdeenmarinaclub.com"},
    {"venue": "Sofitel Saigon Plaza", "name": "EBAN Ymoi", "title": "Front Office Manager", "email": "ymoi.eban@sofitel.com"},
    {"venue": "Hilton Guangzhou Baiyun", "name": "Milk Lin", "title": "Purchasing Manager", "email": "milk.lin@hilton.com"},
    {"venue": "Paresa Resort, Phuket", "name": "Pathama Kanteetaw", "title": "Executive Assistant Manager", "email": "eam@paresaresorts.com"},
    {"venue": "HILTON ZHUZHOU", "name": "Judith Jiang", "title": "Purchasing Manager", "email": "Judith.Jiang@hilton.com"},
    {"venue": "Mercure Bangkok Makkasan", "name": "NIYOMTHANACHAT Sitthisak", "title": "Director of Food & Beverage", "email": "Sitthisak.NIYOMTHANACHAT@accor.com"},
    {"venue": "Fusion Original Saigon Centre", "name": "Marc Bittner", "title": "General Manager", "email": "marc.bittner@fusionhotelgroup.com"},
    {"venue": "Fusion Hotel Group", "name": "Marcus Wirsching", "title": "General Manager MRQN", "email": "Marcus.wirsching@fusionhotelgroup.com"},
    {"venue": "Maxx Royal Bodrum Resort", "name": "Virginia MEZZULLO", "title": "Food & Beverage Director", "email": "Virginia.Mezzullo@maxxroyal.com"},
    {"venue": "Marina Bay Sands", "name": "Pei Wai, Hooi", "title": "Manager, Procurement", "email": "peiwai.hooi@marinabaysands.com"},
    {"venue": "AD LIB HOTEL BANGKOK", "name": "Thitikorn Kanlaya (Din)", "title": "IT Manager", "email": "thitikorn.k@adlibhotels.co"},
    {"venue": "Park Hyatt Abu Dhabi", "name": "Tareq Alnsour", "title": "IT Manager", "email": "tareq.alnsour@hyatt.com"},
    {"venue": "Anantara The Palm Dubai Resort", "name": "Manoj Kumar", "title": "Cluster IT Manager", "email": "mkumar@anantara.com"},
    {"venue": "Ascott Orchard Singapore", "name": "Lionel Leong", "title": "Operations Manager", "email": "lionel.leong@the-ascott.com"},
    {"venue": "Novotel Suites Hanoi", "name": "Vu Thi Duyen", "title": "Chief Accountant", "email": "h9813-gl3@accor.com"},
    {"venue": "MELIÃ BALI", "name": "Achmad Junaedy", "title": "Information Technology Manager", "email": "achmad.junaedy@melia.com"},
    {"venue": "Avista Grande Phuket Karon", "name": "Supakit Kaewthongbua", "title": "Cluster IT Manager", "email": "Supakit.KAEWTHONGBUA@accor.com"},
    {"venue": "Villa Resorts", "name": "Ismail Rasheed", "title": "General Manager", "email": "gm.royal@villaresorts.com"},
    {"venue": "Centara Riverside Hotel Chiang Mai", "name": "Panus Alex Jureeratana", "title": "General Manager", "email": "gmccm@chr.co.th"},
    {"venue": "Hilton Bali Resort", "name": "Wildan Alimudin", "title": "IT Manager", "email": "wildan.alimudin@hilton.com"},
    {"venue": "Mercure Bangkok Sukhumvit", "name": "Suchada Jirapanitcharoen", "title": "Operations Manager", "email": "Suchada.JIRAPANITCHAROEN@accor.com"},
    {"venue": "Grand Mercure Bangkok Atrium", "name": "Artitaya Ponsin", "title": "Executive Assistant Manager", "email": "artitaya.ponsin@accor.com"},
    {"venue": "Ibis Styles Bangkok Silom", "name": "Tosaporn Sukkhasme", "title": "IT Officer", "email": "Tosaporn.SUKKHASEM@accor.com"},
    {"venue": "NOVOTEL Bangkok Ploenchit Sukhumvit", "name": "Chatchawan Thammarowet", "title": "IT Manager", "email": "chatchawan.thammarowet@accor.com"},
    {"venue": "HYATT REGENCY KOH SAMUI", "name": "Ruangdet Roekmuang (Duke)", "title": "IT Manager", "email": "ruangdet.roekmuang@hyatt.com"},
    {"venue": "Thames Valley Khao Yai", "name": "Weerawut Ratikun", "title": "IT Support Supervisor", "email": "itsup@thamesvalleykhaoyai.com"},
    {"venue": "Centara Grand Hotel Osaka", "name": "Naomi Umaki", "title": "IT Manager", "email": "NaomiUm@chr.co.th"},
    {"venue": "PULLMAN HANOI", "name": "CHANGKOON Son", "title": "Operation manager", "email": "Son.CHANGKOON@accor.com"},
    {"venue": "Hotel Nikko Hai Phong", "name": "Tran Thi Nga", "title": "Assistant Purchasing Manager", "email": "pur.mgr@hotelnikkohaiphong.com.vn"},
    {"venue": "ibis Styles Bangkok Ratchada", "name": "Warairat SOMPONG", "title": "General Manager", "email": "Warairat.SOMPONG@accor.com"},
    {"venue": "Away Chiang Mai Thapae Resort", "name": "Katerawee Thepprachum", "title": "General Manager", "email": "katerawee.thepprachum@crosshotelsandresorts.com"},
    {"venue": "The Sanctuary Resort Pattaya", "name": "Matthew Horvat", "title": "General Manager", "email": "gm@sanctuarythailand.com"},
    {"venue": "Centra by Centara Cha-Am Beach Resort Hua Hin", "name": "Asdang Sukwises", "title": "General Manager", "email": "gmcch@chr.co.th"},
    {"venue": "HYATT REGENCY BANGKOK SUKHUMVIT", "name": "Adisak Kompudsa", "title": "Information System Manager", "email": "adisak.kompudsa@hyatt.com"},
    {"venue": "Anantara Lawana Koh Samui Resort", "name": "Sutham Petchsuwan", "title": "IT Manager", "email": "sutham_pe@anantara.com"},
    {"venue": "Park Plaza Bangkok Soi 18", "name": "Arkom Kerdpiam", "title": "IT Manager", "email": "arkom.kerdpiam@parkplaza.com"},
    {"venue": "Ad Lib Bangkok", "name": "Thitikorn Kanlaya", "title": "IT Manager", "email": "thitikorn.k@adlibhotels.co"},
    {"venue": "Akyra Manor Chiang Mai", "name": "Christophe Gestin", "title": "General Manager", "email": "gm.akmc@theakyra.com"},
    {"venue": "Centara Grand Beach Resort & Villas Hua Hin", "name": "Thanakorn Krupanit", "title": "IT Manager", "email": "itchbr@chr.co.th"},
    {"venue": "Centara Grand Mirage Beach Resort Pattaya", "name": "Prasongsin", "title": "Area IT Manager", "email": "cmbritmgr@chr.co.th"},
    {"venue": "Centara Korat", "name": "Kitti", "title": "Hotel Manager", "email": "hmcko@chr.co.th"},
    {"venue": "Centara Pattaya Hotel", "name": "Nathapol Kuywaree (Plome)", "title": "Area Assistant Information Technology Manager", "email": "itcpy@chr.co.th"},
    {"venue": "Centara Grand Beach Resort Phuket", "name": "Prayat Sripakdee (Gugg)", "title": "Area IT Supervisor", "email": "prayatsr@chr.co.th"},
    {"venue": "Mövenpick Myth Hotel Patong Phuket", "name": "Christophe T. Caumont", "title": "General Manager", "email": "christophe.caumont@accor.com"},
    {"venue": "Park Plaza Sukhumvit Bangkok", "name": "Shane Langdon", "title": "General Manager", "email": "shane.l@parkplaza.com"},
    {"venue": "The Landmark Bangkok", "name": "Winit Kitchaiya", "title": "Hotel Manager", "email": "winit.k@landmarkbangkok.com"},
    {"venue": "DoubleTree by Hilton Shah Alam i-City", "name": "Logendran Supramaniam", "title": "IT Manager", "email": "Logendran.Supramaniam@hilton.com"},
    {"venue": "Admiral Hotel Manila MGallery", "name": "Victor Pangilinan", "title": "IT Manager", "email": "victor.pangilinan@accor.com"},
    {"venue": "Heritage Awali Golf & Spa Resort", "name": "Steeve Cassy", "title": "Acting Recreational Manager", "email": "sl@heritageawali.mu"},
    {"venue": "Hilton Darwin", "name": "Vaviano Vui", "title": "IT Manager", "email": "vaviano.vui@hilton.com"},
    {"venue": "Novotel Suites Hanoi", "name": "Hieu Le", "title": "Cluster Information Technology Manager", "email": "hieu.le@accor.com"},
    {"venue": "Novotel Hanoi Thai Ha", "name": "Christophe Pairaud", "title": "General Manager", "email": "christophe.pairaud@accor.com"},
    {"venue": "STAY Wellbeing & Lifestyle Resort", "name": "Kajitpan Teawjaroen (Pun)", "title": "Cluster IT Manager", "email": "itmgr@stayphuketresort.com"},
    {"venue": "DoubleTree by Hilton Phuket Banthai Resort", "name": "Thanongsak Piriyapruet", "title": "Information System Manager", "email": "Thanongsak.Piriyapruet@hilton.com"},
    {"venue": "Amari Kuala Lumpur", "name": "Khafif Japri", "title": "IT Manager", "email": "khafif.japri@amari.com"},
    {"venue": "Park Hyatt Maldives Hadahaa", "name": "Fernando Roman", "title": "Director of Food & Beverage", "email": "fernando.roman@hyatt.com"},
    {"venue": "Atmosphere Kanifushi Maldives", "name": "Titus Babu", "title": "IT Manager", "email": "aitm@atmosphere-kanifushi.com"},
    {"venue": "Novotel Jakarta Cikini", "name": "Sunardi Song", "title": "General Manager", "email": "Sunardi.SONG@accor.com"},
    {"venue": "Hilton Surfers Paradise", "name": "Vanessa Arnott", "title": "Director of Finance", "email": "vanessa.arnott@hilton.com"},
    {"venue": "LOTTE HOTEL HANOI", "name": "Le Tra My", "title": "Marketing & Communications Manager", "email": "my.le@lotte.net"},
    {"venue": "Anantara Al Jabal Al Akhdar Resort", "name": "Siva Sai", "title": "Assistant Information Technology Manager", "email": "ssaimova@anantara.com"},
    {"venue": "HILTON PETALING JAYA", "name": "Jess Ooi", "title": "Purchasing Manager", "email": "Jesselina.Ooi@hilton.com"},
    {"venue": "Hilton Brisbane", "name": "Chris Partridge", "title": "Area General Manager", "email": "Chris.Partridge@hilton.com"},
    {"venue": "Anantara Bazaruto Island Resort", "name": "Yiannis Kosmas", "title": "General Manager", "email": "ykosmas@anantara.com"},
    {"venue": "Centara Mirage Beach Resort Dubai", "name": "Muhammad Arshath", "title": "IT Executive", "email": "MuhammadAr@chr.co.th"},
    {"venue": "IBIS SAMUI BOPHUT", "name": "Jarinya Chochan", "title": "Chief Accountant", "email": "H6688-GL@ACCOR.COM"},
    {"venue": "Hilton Sukhumvit Bangkok", "name": "Saksathit Yingyuen", "title": "Cluster Assistant Food & Beverage Manager", "email": "Saksathit.yingyuen@hilton.com"},
    {"venue": "Centara Grand at Central Plaza Ladprao Bangkok", "name": "Pisutwat Donsuea", "title": "Food & Beverage Manager", "email": "dofbcglb@chr.co.th"},
    {"venue": "Centara Hotel & Convention Centre Udon Thani", "name": "Pacharamonaporn (BEE) Kreuasukhon", "title": "Operations Support Manager & PA to GM", "email": "PacharamonapornKr@chr.co.th"},
    {"venue": "Millennium Hilton Bangkok", "name": "Tim Tate", "title": "General Manager", "email": "Tim.Tate@hilton.com"},
    {"venue": "Anantara Chiang Mai Resort", "name": "Somsak Sanprueksin", "title": "Cluster IT Manager", "email": "somsak_sa@anantara.com"},
    {"venue": "Anantara Hua Hin Resort", "name": "Catarina Simoes", "title": "Resort Manager", "email": "csimoes@anantara.com"},
    {"venue": "Anantara Mai Khao Phuket Villas", "name": "Farin Sriarunlap", "title": "Cluster Administrative Assistant (F&B)", "email": "farin_sr@anantara.com"},
    {"venue": "Avani Khon Kaen Hotel & Convention Centre", "name": "Khwan Doonsang", "title": "IT Supervisor", "email": "khwan_do@avanihotels.com"},
    {"venue": "Amari Buriram United", "name": "Napat Krueanoi", "title": "Secretary to General Manager", "email": "napat.k@amari.com"},
    {"venue": "Amari Don Muang Airport Bangkok", "name": "Piyachai Thongfua", "title": "Manager, Information Technology", "email": "piyachai.t@amari.com"},
    {"venue": "Amari Hua Hin", "name": "Marck Elmenzo", "title": "General Manager", "email": "marck.elmenzo@amari.com"},
    {"venue": "Amari Pattaya", "name": "Phurachet Khantikul", "title": "Manager, IT", "email": "phurachet.k@onyx-hospitality.com"},
    {"venue": "Amari Phuket", "name": "Watana Jinjit", "title": "Manager, IT", "email": "watana.j@onyx-hospitality.com"},
    {"venue": "Amari Koh Samui", "name": "Thanongsak Boripan", "title": "Cluster Assistant Manager, IT", "email": "thanongsak.b@onyx-hospitality.com"},
    {"venue": "Amari Watergate Bangkok", "name": "Visarut Vudthanond", "title": "Manager, Information Technology", "email": "visarut.v@amari.com"},
    {"venue": "Shama Lakeview Asoke Bangkok", "name": "Sirichai Tinakat", "title": "Cluster Manager, IT", "email": "sirichai.t@shama.com"},
    {"venue": "Shama Sukhumvit Bangkok", "name": "Somporn Tanok", "title": "Manager, Finance", "email": "somporn.t@shama.com"},
    {"venue": "Oriental Residence Bangkok", "name": "Phasit C. (Jeep)", "title": "Assistant Manager, F&B", "email": "phasit.c@saffron-collection.com"},
    {"venue": "Pathumwan Princess Hotel", "name": "Pisut Thirangkurat", "title": "Head of Purchasing", "email": "pisut@pprincess.com"},
    {"venue": "The Slate Phuket", "name": "William Daguin", "title": "Hotel Manager", "email": "william@theslatephuket.com"},
    {"venue": "Siam Paragon", "name": "Chanissa Smathivat (Chompoo)", "title": "Department Manager, Customer Services", "email": "chanissa.s@siamparagon.co.th"},
    {"venue": "Modena by Fraser Buriram", "name": "Thapanawat Sakolpat-auttakorn", "title": "Information Technology Manager", "email": "thapanawat.s@modenabyfraser.com"},
    {"venue": "The Ritz-Carlton Residences, Bangkok", "name": "Waraporn Kaewpan", "title": "Assistant Chief Engineer", "email": "Waraporn.kaewpan@ritzcarlton.com"},
    {"venue": "Away Bangkok Riverside Kene", "name": "Jade Simmanee", "title": "IT Manager", "email": "it.abr@awayresorts.com"},
    {"venue": "Amari Havodda Maldives", "name": "Avinash Panda", "title": "Manager IT", "email": "avinash.panda@amari.com"},
    {"venue": "Anantara Quy Nhon Villas", "name": "Bao La", "title": "Cluster IT Manager", "email": "it.vquy@avanihotels.com"},
    {"venue": "Banana Island Resort Doha by Anantara", "name": "Prashan Sathyanadan", "title": "IT Manager", "email": "psathyanadan@anantara.com"},
    {"venue": "Hilton Garden Inn Tabuk", "name": "Mohamed Moraad", "title": "Cluster Assistant I.T Manager", "email": "Mohamed.Moraad@hilton.com"},
    {"venue": "VOCO Orchard Singapore", "name": "Mark Winterton", "title": "General Manager", "email": "mark.winterton@ihg.com"},
    {"venue": "DoubleTree by Hilton Kuala Lumpur", "name": "Lycan Hon", "title": "Operations Manager", "email": "Lycan.Hon@hilton.com"},
    {"venue": "DoubleTree by Hilton Guangzhou", "name": "Thomas Zhang", "title": "Director of Food & Beverage", "email": "Thomas.Zhang@hilton.com"},
    {"venue": "Mercure Vung Tau", "name": "Anh Dang", "title": "Cluster IT Manager", "email": "QuocAnh.DANGNGUYEN@accor.com"},
    {"venue": "Anantara Kalutara Resort", "name": "Rashnu Lokusuriya", "title": "Complex Assistant Finance Controller", "email": "rlokusuriya@anantara.com"},
    {"venue": "Centara Mirage Beach Resort Mui Ne", "name": "Ashish Nehra", "title": "Executive Assistant Manager – Food and Beverage", "email": "eamfbcmv@chr.co.th"},
    {"venue": "Melia Ho Tram Beach Resort", "name": "Linh Le", "title": "Guest Experience Manager", "email": "linh.le@melia.com"},
    {"venue": "Paradise Island Resort", "name": "Mohamed Iujaz Zuhair", "title": "Resort Manager", "email": "rm@paradise-island.com.mv"},
    {"venue": "SOL by Meliá Phu Quoc", "name": "Lance Navarra Leong", "title": "Operations Manager", "email": "om@solbymeliaphuquoc.net"},
    {"venue": "Park Regis Singapore", "name": "Dennis Bonabon", "title": "IT Manager", "email": "itmprsi@parkregissingapore.com"},
    {"venue": "Amari Vang Vieng Laos", "name": "Sukson Soosongdee", "title": "Manager IT", "email": "sukson.s@amari.com"},
    {"venue": "Sun Siyam Iru Fushi", "name": "Ambareesh CM", "title": "IT Manager", "email": "ambareesh.cm@sunsiyam.com"},
    {"venue": "Night Hotel Bangkok", "name": "Matthieu Reynaud", "title": "General Manager", "email": "Mreynaud@nighthotels.com"},
    {"venue": "Hotel Nikko Bangkok", "name": "Chatchai (Joe) Klinson", "title": "IT Manager", "email": "itm@nikkobangkok.com"},
    {"venue": "DoubleTree by Hilton Karaka", "name": "Aniket Chitre", "title": "Cluster Information Technology Manager", "email": "aniket.chitre@hilton.com"},
    {"venue": "Hilton Auckland", "name": "Aniket Chitre", "title": "Cluster Information Technology Manager", "email": "aniket.chitre@hilton.com"},
    {"venue": "Hilton Lake Taupo", "name": "Aniket Chitre", "title": "Cluster Information Technology Manager", "email": "aniket.chitre@hilton.com"},
    {"venue": "HILTON SINGAPORE ORCHARD", "name": "Linges Waren", "title": "Director of Food & Beverage", "email": "Linges.Waren@Hilton.com"},
    {"venue": "Hilton Kota Kinabalu", "name": "Hansie Phillip", "title": "Information Technology Manager", "email": "hansie.phillip@hilton.com"},
    {"venue": "Sofitel Angkor Phokeethra Golf & Spa Resort", "name": "Kola Len", "title": "IT Manager", "email": "Kola.LEN@sofitel.com"},
    {"venue": "OBLU by Atmosphere at Helengeli", "name": "Subhash Chodankar", "title": "Assistant IT Manager", "email": "aitm@oblu-helengeli.com"},
    {"venue": "Shangri-La Qingdao", "name": "Leo Zhang", "title": "Information Technology Manager", "email": "leo.zhang@shangri-la.com"},
    {"venue": "IBIS SAIGON AIRPORT", "name": "Tuan Anh Nguyen", "title": "IT Senior Supervisor", "email": "h9468-it@accor.com"},
    {"venue": "NOVOTEL PHU QUOC RESORT", "name": "Hang Nguyen", "title": "Financial Controller", "email": "Hang.NGUYEN@accor.com"},
    {"venue": "Pullman Phuket Karon Beach Resort", "name": "Christian Carminati", "title": "Hotel Manager", "email": "christian.carminati@accor.com"},
    {"venue": "X2 Vibe Bangkok Sukhumvit Hotel", "name": "Kathawut Choopreechayut", "title": "IT Manager", "email": "it.suk@x2vibe.com"},
    {"venue": "Centara Hotel Hat Yai", "name": "Withul Sakaro", "title": "Financial Controller", "email": "fcchy@chr.co.th"},
    {"venue": "Centara Koh Chang Tropicana Resort", "name": "Punyaphat Kamonkorn", "title": "Food & Beverage Manager", "email": "fbckc@chr.co.th"},
    {"venue": "Centara Ubon", "name": "Mitree Suwannapet (Fam)", "title": "Financial Controller", "email": "fccub@chr.co.th"},
    {"venue": "Shama Yen-Akat Bangkok", "name": "Sirayut Srijaloen", "title": "IT Manager", "email": "sirayut.s@shama.com"},
    {"venue": "Hotel Nikko Amata City Chonburi", "name": "Suthinee Hirio (Su)", "title": "Director of Rooms", "email": "dor@hotelnikko-amatacity.com"},
    {"venue": "Mode Sathorn Hotel", "name": "Maneepitcha Songkijzup (May)", "title": "Sales Coordinator", "email": "salesco@modesathorn.com"},
    {"venue": "Paresa Resort Phuket", "name": "Thanachai Niramol (Aey)", "title": "Information Technology Manager", "email": "itm@paresaresorts.com"},
    {"venue": "The Aberdeen Marina Club", "name": "Ricky Hui", "title": "Assistant Director of Food & Beverage", "email": "ricky.hui@aberdeenmarinaclub.com"}
]

# Read the current venue_data.md
with open('/Users/benorbe/Documents/BMAsia Social Hub/backend/venue_data.md', 'r') as f:
    lines = f.readlines()

# Process each contact
updated = 0
for contact in contacts_data:
    venue_name = contact['venue']

    # Find the venue in the file
    for i, line in enumerate(lines):
        if line.startswith('### '):
            current_venue = line.replace('### ', '').strip()

            # Try to match venue names (case insensitive, partial match)
            if venue_name.lower() in current_venue.lower() or current_venue.lower() in venue_name.lower():
                # Found matching venue
                print(f"Updating {current_venue} with contact: {contact['name']}")

                # Find the Contacts section
                j = i + 1
                while j < len(lines) and not lines[j].startswith('### '):
                    if '#### Contacts' in lines[j]:
                        # Update the General Manager line
                        k = j + 1
                        while k < len(lines) and not lines[k].startswith('###') and not lines[k].startswith('####'):
                            if '- **General Manager**:' in lines[k]:
                                # Update the contact info
                                lines[k] = f"- **General Manager**: {contact['name']}\n"
                                if k + 1 < len(lines) and '- Email:' in lines[k + 1]:
                                    lines[k + 1] = f"  - Email: {contact['email']}\n"
                                if k + 2 < len(lines) and '- Phone:' in lines[k + 2]:
                                    # Keep existing phone or add placeholder
                                    if '—' in lines[k + 2]:
                                        lines[k + 2] = "  - Phone: —\n"
                                updated += 1
                                break
                            k += 1
                        break
                    j += 1
                break

print(f"\nUpdated {updated} venues with contact information")

# Write back to file
with open('/Users/benorbe/Documents/BMAsia Social Hub/backend/venue_data.md', 'w') as f:
    f.writelines(lines)

print("venue_data.md has been updated!")