"""Fictional hotel policies in English and Polish for the Hotel Employee Policy Assistant."""

HOTEL_RULES = [
    {
        "rule_id": "VIP-EN-01",
        "category": "VIP Codes",
        "language": "en",
        "title": "VIP Tier Codes & Perks (AMBER-77, SAPPHIRE-12, CORAL-05)",
        "content": (
            "At Grand Baltic Sovereign Hotel, employee-facing VIP status codes are strictly confidential: "
            "Code 'AMBER-77' designates Diplomatic Immunity Guests (complimentary Presidential Suite upgrade, "
            "private elevator PIN 4491, and 100% minibar waiver). "
            "Code 'SAPPHIRE-12' designates Royal & A-List Celebrity Guests (mandatory staff NDA at check-in, "
            "24/7 private butler at extension #880, and free late checkout until 18:00). "
            "Code 'CORAL-05' designates Returning Board Partners (complimentary airport helipad transfer and a 150 EUR Baltic Amber Spa voucher)."
        ),
    },
    {
        "rule_id": "VIP-PL-01",
        "category": "VIP Codes",
        "language": "pl",
        "title": "Kody Statusu VIP i Przywileje (AMBER-77, SAPPHIRE-12, CORAL-05)",
        "content": (
            "W Hotelu Bałtycki Suweren kody statusu VIP dla personelu są ściśle poufne: "
            "Kod 'AMBER-77' oznacza Gości z Immunitetem Dyplomatycznym (bezpłatny upgrade do Apartamentu Prezydenckiego, "
            "kod PIN do prywatnej windy 4491 oraz 100% zwolnienia z opłat za minibar). "
            "Kod 'SAPPHIRE-12' oznacza Gości Królewskich i Celebrytów (obowiązkowa umowa NDA przy zameldowaniu, "
            "prywatny kamerdyner 24/7 pod numerem wew. #880 oraz bezpłatne późne wymeldowanie do 18:00). "
            "Kod 'CORAL-05' oznacza Partnerów Zarządu (bezpłatny transfer śmigłowcem z lotniska oraz voucher o wartości 150 EUR do Baltic Amber Spa)."
        ),
    },
    {
        "rule_id": "PET-EN-01",
        "category": "Pet Fees",
        "language": "en",
        "title": "Pet Admission, Nightly Fees & Exemptions",
        "content": (
            "Grand Baltic Sovereign Hotel welcomes domestic dogs, cats, and ferrets up to 18 kg (max 2 pets per room). "
            "The standard pet sanitation fee is 140 PLN (35 EUR) per pet per night, plus a refundable 500 PLN bio-cleaning deposit collected at check-in. "
            "Certified guide/service animals and guests holding VIP code 'AMBER-77' or 'SAPPHIRE-12' are 100% exempt from both the nightly pet fee and the deposit. "
            "Pets are prohibited in the 9th-floor Thermal Pool, but reception staff must issue a complimentary Baltic salmon welcome kit using POS code 'PAW-WELCOME'."
        ),
    },
    {
        "rule_id": "PET-PL-01",
        "category": "Pet Fees",
        "language": "pl",
        "title": "Zwierzęta w Hotelu: Opłaty Dobowe, Kaucja i Zwolnienia",
        "content": (
            "Hotel Bałtycki Suweren akceptuje psy, koty oraz fretki domowe o wadze do 18 kg (maksymalnie 2 zwierzęta na pokój). "
            "Standardowa opłata sanitarna wynosi 140 PLN (35 EUR) za zwierzę za dobę oraz zwrotna kaucja ekologiczna 500 PLN pobierana przy zameldowaniu. "
            "Certyfikowane psy asystujące oraz goście posiadający kod VIP 'AMBER-77' lub 'SAPPHIRE-12' są w 100% zwolnieni zarówno z opłaty dobowej, jak i kaucji. "
            "Zwierzęta mają zakaz wstępu na basen termalny na 9. piętrze, natomiast recepcja ma obowiązek wydać bezpłatny pakiet powitalny z łososiem bałtyckim (kod POS 'PAW-WELCOME')."
        ),
    },
    {
        "rule_id": "CHK-EN-01",
        "category": "Late Checkout",
        "language": "en",
        "title": "Standard & Late Checkout Pricing and Approval Codes",
        "content": (
            "Standard checkout time is 11:00 AM. "
            "Late checkout until 14:00 costs a flat fee of 120 PLN (28 EUR) and may be approved directly by any front-desk receptionist using POS override code 'LATE-14'. "
            "Late checkout between 14:00 and 17:00 is billed at 50% of the nightly room rate and requires Duty Manager authorization (extension #202, code 'MGR-HALF'). "
            "Any checkout after 17:00 is charged 100% of the nightly rate, except for guests with VIP code 'SAPPHIRE-12' or 'AMBER-77' who receive complimentary checkout until 18:00."
        ),
    },
    {
        "rule_id": "CHK-PL-01",
        "category": "Late Checkout",
        "language": "pl",
        "title": "Godziny Wymeldowania, Opłaty za Późne Wymeldowanie i Kody POS",
        "content": (
            "Standardowa godzina wymeldowania to 11:00. "
            "Późne wymeldowanie do godziny 14:00 kosztuje ryczałtowo 120 PLN (28 EUR) i może zostać zatwierdzone samodzielnie przez recepcjonistę za pomocą kodu POS 'LATE-14'. "
            "Późne wymeldowanie między 14:00 a 17:00 kosztuje 50% stawki dobowej za pokój i wymaga autoryzacji Kierownika Zmiany (wew. #202, kod 'MGR-HALF'). "
            "Wymeldowanie po godzinie 17:00 jest naliczane jako 100% stawki dobowej, z wyjątkiem gości z kodem VIP 'SAPPHIRE-12' lub 'AMBER-77', którym przysługuje bezpłatne wymeldowanie do 18:00."
        ),
    },
    {
        "rule_id": "SEC-EN-01",
        "category": "Security & Vault",
        "language": "en",
        "title": "Night Shift Security Protocol & Keycard Replacement",
        "content": (
            "Front-desk staff must never announce guest room numbers aloud. "
            "Issuing a replacement keycard requires either government photo ID verification or the guest's 4-digit check-in PIN. "
            "For silent security emergencies at reception, employees must dial extension #999 and state code word 'NEPTUNE-RED'. "
            "Master keycards are stored in Biometric Vault B-9 and automatically deactivate after 4 hours."
        ),
    },
    {
        "rule_id": "SEC-PL-01",
        "category": "Security & Vault",
        "language": "pl",
        "title": "Protokół Bezpieczeństwa Nocnej Zmiany i Duplikaty Kart",
        "content": (
            "Pracownicy recepcji nigdy nie mogą wymawiać na głos numerów pokoi gości. "
            "Wydanie duplikatu karty pokojowej wymaga weryfikacji dokumentu tożsamości ze zdjęciem lub podania 4-cyfrowego kodu PIN z zameldowania. "
            "W przypadku cichego alarmu bezpieczeństwa w recepcji pracownik musi wybrać numer wew. #999 i podać hasło 'NEPTUNE-RED'. "
            "Karty mistrzowskie (Master) znajdują się w Sejfie Biometrycznym B-9 i dezaktywują się automatycznie po 4 godzinach."
        ),
    },
]
