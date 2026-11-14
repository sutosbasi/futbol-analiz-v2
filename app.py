import os
import re
import pandas as pd
import unicodedata
from flask import Flask, request, render_template, jsonify
from supabase import create_client

# ============================================
# FLASK UYGULAMA BAŞLATICI (Gunicorn'un aradığı 'app')
# ============================================
app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wrclidclyqmysddmhpgk.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_uBlT0hrxqHXNjGH-Gp0saA_2uM8Pq0I")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

GUNCEL_SEZON = "2026-2027"

# ============================================
# TAKIM ADI NORMALİZASYONU
# ============================================
ALIAS = {
    # === PREMIER LİG ===
    'arsenal': 'Arsenal', 'aston villa': 'Aston Villa',
    'afc bournemouth': 'Bournemouth', 'bournemouth': 'Bournemouth',
    'brentford': 'Brentford',
    'brighton & hove albion': 'Brighton', 'brighton and hove albion': 'Brighton', 'brighton': 'Brighton',
    'chelsea': 'Chelsea', 'coventry city': 'Coventry City', 'coventry': 'Coventry City',
    'crystal palace': 'Crystal Palace', 'everton': 'Everton', 'fulham': 'Fulham',
    'hull city': 'Hull City', 'hull': 'Hull City',
    'ipswich town': 'Ipswich Town', 'ipswich': 'Ipswich Town',
    'leeds united': 'Leeds United', 'leeds': 'Leeds United',
    'liverpool': 'Liverpool',
    'manchester city': 'Manchester City', 'man city': 'Manchester City',
    'manchester united': 'Manchester United', 'manchester utd': 'Manchester United', 'man united': 'Manchester United',
    'newcastle united': 'Newcastle', 'newcastle': 'Newcastle',
    'nottingham forest': 'Nottingham Forest', "nott'm forest": 'Nottingham Forest', 'nottm forest': 'Nottingham Forest', 'nottingham': 'Nottingham Forest',
    'sunderland': 'Sunderland',
    'tottenham hotspur': 'Tottenham Hotspur', 'tottenham': 'Tottenham Hotspur', 'spurs': 'Tottenham Hotspur',
    'west ham united': 'West Ham', 'west ham': 'West Ham',
    'wolverhampton wanderers': 'Wolverhampton Wanderers', 'wolverhampton': 'Wolverhampton Wanderers', 'wolves': 'Wolverhampton Wanderers',
    'sheffield united': 'Sheffield Utd', 'sheffield utd': 'Sheffield Utd',
    'west bromwich albion': 'West Brom', 'west brom': 'West Brom',
    'norwich city': 'Norwich', 'norwich': 'Norwich',
    'cardiff city': 'Cardiff', 'cardiff': 'Cardiff',
    'huddersfield town': 'Huddersfield', 'huddersfield': 'Huddersfield',
    'swansea city': 'Swansea', 'swansea': 'Swansea',
    'stoke city': 'Stoke', 'stoke': 'Stoke',
    'leicester city': 'Leicester', 'leicester': 'Leicester',
    'luton town': 'Luton Town', 'luton': 'Luton Town',
    'watford': 'Watford', 'burnley': 'Burnley', 'southampton': 'Southampton',

    # === LA LIGA ===
    'deportivo alaves': 'Alavés', 'alaves': 'Alavés',
    'athletic club bilbao': 'Athletic Club', 'athletic club': 'Athletic Club', 'athletic bilbao': 'Athletic Club',
    'atletico de madrid': 'Atlético Madrid', 'atletico madrid': 'Atlético Madrid',
    'fc barcelona': 'Barcelona', 'barcelona': 'Barcelona',
    'celta de vigo': 'Celta Vigo', 'rc celta de vigo': 'Celta Vigo', 'rc celta': 'Celta Vigo', 'celta vigo': 'Celta Vigo',
    'dep. a coruna': 'Dep. A Coruña', 'deportivo la coruna': 'Dep. A Coruña', 'deportivo a coruna': 'Dep. A Coruña',
    'elche cf': 'Elche', 'elche': 'Elche',
    'rcd espanyol': 'Espanyol', 'espanyol': 'Espanyol',
    'getafe cf': 'Getafe', 'getafe': 'Getafe',
    'levante': 'Levante', 'malaga': 'Málaga',
    'ca osasuna': 'Osasuna', 'osasuna': 'Osasuna',
    'racing sant': 'Racing Sant', 'racing santander': 'Racing Sant',
    'rayo vallecano': 'Rayo Vallecano',
    'real betis': 'Real Betis', 'real madrid': 'Real Madrid',
    'real sociedad': 'Real Sociedad', 'real sociedad de futbol': 'Real Sociedad',
    'sevilla fc': 'Sevilla', 'sevilla': 'Sevilla',
    'valencia cf': 'Valencia', 'valencia': 'Valencia',
    'villarreal cf': 'Villarreal', 'villarreal': 'Villarreal',
    'granada cf': 'Granada', 'granada': 'Granada',
    'real valladolid': 'Real Valladolid', 'valladolid': 'Real Valladolid',
    'cadiz': 'Cádiz', 'almeria': 'Almería',
    'girona fc': 'Girona', 'girona': 'Girona',
    'rcd mallorca': 'RCD Mallorca', 'mallorca': 'RCD Mallorca',

    # === LIGUE 1 ===
    'angers sco': 'Angers', 'angers': 'Angers',
    'aj auxerre': 'Auxerre', 'auxerre': 'Auxerre',
    'stade brestois': 'Brest', 'stade brestois 29': 'Brest', 'brest': 'Brest',
    'le havre ac': 'Le Havre', 'le havre': 'Le Havre',
    'le mans fc': 'Le Mans', 'le mans': 'Le Mans',
    'rc lens': 'Lens', 'lens': 'Lens',
    'losc lille': 'Lille', 'lille osc': 'Lille', 'lille': 'Lille',
    'fc lorient': 'Lorient', 'lorient': 'Lorient',
    'olympique lyonnais': 'Lyon', 'lyon': 'Lyon',
    'olympique de marseille': 'Marseille', 'olympique marseille': 'Marseille', 'marseille': 'Marseille',
    'as monaco': 'Monaco', 'monaco': 'Monaco',
    'ogc nice': 'Nice', 'nice': 'Nice',
    'paris saint-germain': 'PSG', 'paris saint germain': 'PSG', 'paris sg': 'PSG',
    'paris fc': 'Paris FC',
    'stade rennais': 'Rennes', 'rennes': 'Rennes',
    'rc strasbourg': 'Strasbourg', 'strasbourg': 'Strasbourg',
    'toulouse fc': 'Toulouse', 'toulouse': 'Toulouse',
    'es troyes ac': 'Troyes', 'troyes': 'Troyes',
    'as saint-etienne': 'Saint-Etienne', 'saint-etienne': 'Saint-Etienne',
    'clermont foot': 'Clermont Foot',
    'fc metz': 'Metz', 'metz': 'Metz',
    'montpellier hsc': 'Montpellier', 'montpellier': 'Montpellier',
    'fc nantes': 'Nantes', 'nantes': 'Nantes',
    'stade de reims': 'Reims', 'reims': 'Reims',

    # === SERIE A ===
    'atalanta bc': 'Atalanta', 'atalanta': 'Atalanta',
    'bologna': 'Bologna', 'cagliari': 'Cagliari', 'como': 'Como',
    'acf fiorentina': 'Fiorentina', 'fiorentina': 'Fiorentina',
    'frosinone': 'Frosinone', 'genoa': 'Genoa',
    'internazionale': 'Inter Milan', 'inter milan': 'Inter Milan', 'inter': 'Inter Milan',
    'juventus': 'Juventus',
    'ss lazio': 'Lazio', 'lazio': 'Lazio',
    'lecce': 'Lecce',
    'ac milan': 'Milan', 'milan': 'Milan',
    'monza': 'Monza',
    'ssc napoli': 'Napoli', 'napoli': 'Napoli',
    'parma': 'Parma',
    'as roma': 'Roma', 'roma': 'Roma',
    'sassuolo': 'Sassuolo', 'torino': 'Torino', 'udinese': 'Udinese', 'venezia': 'Venezia',
    'salernitana': 'Salernitana', 'empoli': 'Empoli',
    'hellas verona': 'Hellas Verona', 'verona': 'Hellas Verona',

    # === BUNDESLIGA ===
    'fc augsburg': 'Augsburg', 'augsburg': 'Augsburg',
    'fc bayern munchen': 'Bayern Munich', 'bayern munchen': 'Bayern Munich', 'bayern munich': 'Bayern Munich',
    'borussia dortmund': 'Dortmund', 'dortmund': 'Dortmund',
    'sv elversberg': 'Elversberg', 'elversberg': 'Elversberg',
    'eintracht frankfurt': 'Frankfurt', 'frankfurt': 'Frankfurt',
    'sc freiburg': 'Freiburg', 'freiburg': 'Freiburg',
    'borussia monchengladbach': 'Gladbach', "m'gladbach": 'Gladbach', 'monchengladbach': 'Gladbach', 'gladbach': 'Gladbach',
    'hamburger sv': 'Hamburger SV', 'hamburg': 'Hamburger SV',
    '1. fc heidenheim': 'Heidenheim', 'fc heidenheim': 'Heidenheim', 'heidenheim': 'Heidenheim',
    'tsg hoffenheim': 'Hoffenheim', 'hoffenheim': 'Hoffenheim',
    '1. fc koln': 'Köln', 'fc koln': 'Köln', 'koln': 'Köln',
    'bayer leverkusen': 'Leverkusen', 'leverkusen': 'Leverkusen',
    '1. fsv mainz 05': 'Mainz 05', 'mainz 05': 'Mainz 05', 'mainz': 'Mainz 05',
    'sc paderborn 07': 'Paderborn 07', 'paderborn 07': 'Paderborn 07', 'paderborn': 'Paderborn 07',
    'rb leipzig': 'RB Leipzig', 'leipzig': 'RB Leipzig',
    'fc schalke 04': 'Schalke 04', 'schalke 04': 'Schalke 04', 'schalke': 'Schalke 04',
    'vfb stuttgart': 'Stuttgart', 'stuttgart': 'Stuttgart',
    '1. fc union berlin': 'Union Berlin', 'union berlin': 'Union Berlin',
    'sv werder bremen': 'Werder Bremen', 'werder bremen': 'Werder Bremen', 'bremen': 'Werder Bremen',
    'vfl wolfsburg': 'Wolfsburg', 'wolfsburg': 'Wolfsburg',
    'hertha bsc': 'Hertha Berlin', 'hertha berlin': 'Hertha Berlin',
    'sv darmstadt 98': 'Darmstadt', 'darmstadt': 'Darmstadt',
    'vfl bochum': 'Bochum', 'bochum': 'Bochum',
    'arminia bielefeld': 'Arminia Bielefeld',
    'spvgg greuther furth': 'Greuther Fürth', 'greuther furth': 'Greuther Fürth',
    'holstein kiel': 'Holstein Kiel',
    'fc st. pauli': 'FC St. Pauli', 'st. pauli': 'FC St. Pauli', 'st pauli': 'FC St. Pauli',
    'fortuna dusseldorf': 'Fortuna Düsseldorf',

    # === SÜPER LİG ===
    'alanyaspor': 'Alanyaspor',
    'amedspor': 'Amedspor', 'amed sportif': 'Amedspor',
    'istanbul basaksehir': 'Başakşehir', 'istanbul başakşehir': 'Başakşehir', 'basaksehir': 'Başakşehir', 'başakşehir': 'Başakşehir',
    'beşiktaş': 'Beşiktaş', 'besiktas': 'Beşiktaş',
    'erzurum bb': 'Erzurum BB', 'erzurumspor': 'Erzurum BB', 'erzurum': 'Erzurum BB', 'bb erzurumspor': 'Erzurum BB',
    'eyüpspor': 'Eyüpspor', 'eyupspor': 'Eyüpspor',
    'fenerbahçe': 'Fenerbahçe', 'fenerbahce': 'Fenerbahçe',
    'galatasaray': 'Galatasaray',
    'gaziantep fk': 'Gaziantep', 'gaziantep': 'Gaziantep', 'gaziantepspor': 'Gaziantep', 'gaziantep bld': 'Gaziantep',
    'gençlerbirliği': 'Gençlerbirliği', 'genclerbirligi': 'Gençlerbirliği',
    'göztepe': 'Göztepe', 'goztepe': 'Göztepe',
    'kasımpaşa': 'Kasımpaşa', 'kasimpasa': 'Kasımpaşa',
    'kocaelispor': 'Kocaelispor',
    'konyaspor': 'Konyaspor',
    'çaykur rizespor': 'Rizespor', 'caykur rizespor': 'Rizespor', 'rizespor': 'Rizespor',
    'samsunspor': 'Samsunspor',
    'trabzonspor': 'Trabzonspor',
    'yeni çorumspor': 'Yeni Çorumspor', 'yeni corumspor': 'Yeni Çorumspor', 'corumspor': 'Yeni Çorumspor',
    'kayserispor': 'Kayserispor', 'hatayspor': 'Hatayspor',
    'karagümrük': 'Karagümrük', 'karagumruk': 'Karagümrük', 'fatih karagümrük': 'Karagümrük',
    'istanbulspor': 'İstanbulspor', 'pendikspor': 'Pendikspor',
    'sivasspor': 'Sivasspor', 'antalyaspor': 'Antalyaspor',
    'giresunspor': 'Giresunspor',
    'ümraniyespor': 'Ümraniyespor', 'umraniyespor': 'Ümraniyespor',
    'y. malatyaspor': 'Y. Malatyaspor', 'yeni malatyaspor': 'Y. Malatyaspor', 'malatyaspor': 'Y. Malatyaspor',
    'bb bodrumspor': 'BB Bodrumspor', 'bodrumspor': 'BB Bodrumspor',
    'adana demirspor': 'Adana Demirspor', 'adana': 'Adana Demirspor',
    'denizlispor': 'Denizlispor',
    'mke ankaragücü': 'MKE Ankaragücü', 'ankaragücü': 'MKE Ankaragücü', 'ankaragucu': 'MKE Ankaragücü',
    'altay': 'Altay',
}

EXACT_ALIAS = {
    'fb': 'Fenerbahçe', 'gs': 'Galatasaray', 'bjk': 'Beşiktaş', 'ts': 'Trabzonspor',
    'barca': 'Barcelona', 'hsv': 'Hamburger SV', 'bvb': 'Dortmund',
}

SORTED_ALIAS_KEYS = sorted(ALIAS.keys(), key=len, reverse=True)


def _base_key(t):
    if pd.isna(t) or t is None:
        return ''
    s = str(t).strip()
    for c in ('\u200b', '\u200c', '\u200d', '\ufeff'):
        s = s.replace(c, '')
    s = s.lower()
    for tr, en in [('ı', 'i'), ('İ', 'i'), ('i̇', 'i'), ('ş', 's'), ('ğ', 'g'),
                    ('ü', 'u'), ('ö', 'o'), ('ç', 'c')]:
        s = s.replace(tr, en)
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def get_canonical_name(t):
    if pd.isna(t) or t is None:
        return ''
    raw = str(t).strip()
    if not raw:
        return ''
    key = _base_key(raw)
    if not key:
        return ''
    if key in EXACT_ALIAS:
        return EXACT_ALIAS[key]
    if key in ALIAS:
        return ALIAS[key]
    for k in SORTED_ALIAS_KEYS:
        if k in key:
            return ALIAS[k]
    return raw


def normalize_key(t):
    if pd.isna(t) or t is None:
        return ''
    return _base_key(get_canonical_name(t))


def clean_numeric(val):
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    s = re.sub(r'^[sS]\s*', '', s)
    s = s.replace(' ', '')
    if re.match(r'^-?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?$', s):
        if '.' in s and ',' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) == 3:
                s = s.replace(',', '')
            else:
                s = s.replace(',', '.')
        elif '.' in s:
            parts = s.split('.')
            if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
                s = s.replace('.', '')
    else:
        s = s.replace(',', '.')
    s = re.sub(r'[^\d.\-]', '', s)
    try:
        return float(s)
    except ValueError:
        return 0.0


def fetch_data(table_name):
    records = []
    start = 0
    limit = 1000
    try:
        print(f"[DEBUG] {table_name} tablosundan veri çekiliyor...")
        while True:
            res = supabase.table(table_name).select("*").range(start, start + limit - 1).execute()
            data = res.data if res and res.data else []
            if not data:
                break
            records.extend(data)
            if len(data) < limit:
                break
            start += limit
        print(f"[DEBUG] {table_name} başarıyla çekildi. Toplam: {len(records)}")
        return records
    except Exception as e:
        print(f"[X] Supabase Çekme Hatası ({table_name}): {e}")
        return records


print("=" * 60)
print("Supabase Verileri Yükleniyor...")

maclar_data = fetch_data("fb_maclar")
takimlar_data = fetch_data("fb_takim_verileri")

maclar = pd.DataFrame(maclar_data) if maclar_data else pd.DataFrame()
takimlar = pd.DataFrame(takimlar_data) if takimlar_data else pd.DataFrame()

print(f"[BILGI] Maç Satır Sayısı: {len(maclar)}")
print(f"[BILGI] Takım Verisi Satır Sayısı: {len(takimlar)}")

COLUMN_MAP_MAC = {
    'date': 'Date', 'tarih': 'Date',
    'home': 'Home', 'ev_sahibi': 'Home', 'home_team': 'Home', 'ev': 'Home',
    'away': 'Away', 'deplasman': 'Away', 'away_team': 'Away', 'dep': 'Away',
    'homegoals': 'HomeGoals', 'ev_gol': 'HomeGoals', 'home_score': 'HomeGoals',
    'awaygoals': 'AwayGoals', 'dep_gol': 'AwayGoals', 'away_score': 'AwayGoals',
    'lig': 'Lig', 'league': 'Lig',
    'sezon': 'Sezon', 'season': 'Sezon'
}

if not maclar.empty:
    new_cols = {c: COLUMN_MAP_MAC.get(str(c).lower().strip(), c) for c in maclar.columns}
    maclar.rename(columns=new_cols, inplace=True)
    if 'Date' in maclar.columns:
        maclar['Date'] = pd.to_datetime(maclar['Date'], errors='coerce')
    if {'Home', 'Away'}.issubset(maclar.columns):
        maclar['Home_Display'] = maclar['Home'].apply(get_canonical_name)
        maclar['Away_Display'] = maclar['Away'].apply(get_canonical_name)
        maclar['_key_home'] = maclar['Home_Display'].apply(normalize_key)
        maclar['_key_away'] = maclar['Away_Display'].apply(normalize_key)
    if {'HomeGoals', 'AwayGoals'}.issubset(maclar.columns):
        maclar['HomeGoals'] = pd.to_numeric(maclar['HomeGoals'], errors='coerce').fillna(0)
        maclar['AwayGoals'] = pd.to_numeric(maclar['AwayGoals'], errors='coerce').fillna(0)

if not takimlar.empty:
    for col in ['MP', 'Gls', 'Ast', 'CrdY', 'CrdR', 'Sh', 'SoT', 'Keeper_GA', 'Possession']:
        if col not in takimlar.columns:
            takimlar[col] = 0.0

    for col in takimlar.columns:
        lc = str(col).lower().strip()
        if lc in ['squad', 'takim', 'team', 'takım']:
            takimlar['Squad'] = takimlar[col]
        elif lc in ['mp', 'oynanan_mac', 'mac', 'maç', 'matches_played']:
            takimlar['MP'] = takimlar[col].apply(clean_numeric)
        elif lc in ['gls', 'gol', 'goals', 'atilan_gol']:
            takimlar['Gls'] = takimlar[col].apply(clean_numeric)
        elif lc in ['ast', 'asist', 'assists']:
            takimlar['Ast'] = takimlar[col].apply(clean_numeric)
        elif lc in ['crdy', 'yellow_cards', 'sari_kart', 'sarı_kart']:
            takimlar['CrdY'] = takimlar[col].apply(clean_numeric)
        elif lc in ['crdr', 'red_cards', 'kirmizi_kart', 'kırmızı_kart']:
            takimlar['CrdR'] = takimlar[col].apply(clean_numeric)
        elif lc in ['sh', 'shots', 'sut', 'şut']:
            takimlar['Sh'] = takimlar[col].apply(clean_numeric)
        elif lc in ['sot', 'shots_on_target', 'isabetli_sut', 'isabetli_şut']:
            takimlar['SoT'] = takimlar[col].apply(clean_numeric)
        elif lc in ['keeper_ga', 'ga', 'goals_against', 'yenen_gol', 'yendigi_gol', 'goals_against_per90']:
            takimlar['Keeper_GA'] = takimlar[col].apply(clean_numeric)
        elif lc in ['poss', 'possession', 'topla_oynama']:
            takimlar['Possession'] = takimlar[col].apply(clean_numeric)
        elif lc in ['lig', 'league']:
            takimlar['Lig'] = takimlar[col]
        elif lc in ['sezon', 'season']:
            takimlar['Sezon'] = takimlar[col]

    if 'Squad' in takimlar.columns:
        takimlar['Squad_Display'] = takimlar['Squad'].apply(get_canonical_name)
        takimlar['_key_squad'] = takimlar['Squad_Display'].apply(normalize_key)

LIG_TAKIMLARI = {}
all_ligler = set()
if not maclar.empty and 'Lig' in maclar.columns:
    all_ligler.update(maclar['Lig'].dropna().unique())
if not takimlar.empty and 'Lig' in takimlar.columns:
    all_ligler.update(takimlar['Lig'].dropna().unique())

for lig in sorted(all_ligler):
    lig_str = str(lig).strip()
    if not lig_str:
        continue
    teams = set()
    if not takimlar.empty and 'Lig' in takimlar.columns:
        lt = takimlar[takimlar['Lig'] == lig]
        teams.update(lt['Squad_Display'].dropna().unique())
    if not maclar.empty and 'Lig' in maclar.columns:
        lm = maclar[maclar['Lig'] == lig]
        teams.update(lm['Home_Display'].dropna().unique())
        teams.update(lm['Away_Display'].dropna().unique())
    teams = {t for t in teams if t and str(t).strip() != ''}
    if teams:
        LIG_TAKIMLARI[lig_str] = sorted(list(teams))

print(f"YÜKLEME BAŞARILI: {len(LIG_TAKIMLARI)} lig hazır.")
print("=" * 60)


# ============================================
# İSTATİSTİK FONKSİYONLARI
# ============================================
def match_team_key(df_col, key):
    return df_col == key


def _tv_get(tv, name, default=0.0):
    for k in (name, name.lower(), name.upper()):
        if k in tv:
            v = tv[k]
            if v is None:
                continue
            if isinstance(v, float) and pd.isna(v):
                continue
            return clean_numeric(v)
    return default


def guc_puani_hesapla(tv):
    mp = _tv_get(tv, 'MP') or 1
    gls = _tv_get(tv, 'Gls')
    ga = _tv_get(tv, 'Keeper_GA')
    sh = _tv_get(tv, 'Sh')
    sot = _tv_get(tv, 'SoT')
    poss = _tv_get(tv, 'Possession')

    mp = max(1.0, mp)
    sot_pct = (sot / sh * 100) if sh > 0 else 0
    g_sh = (gls / sh) if sh > 0 else 0
    g_sot = (gls / sot) if sot > 0 else 0

    puan = min(30, (gls / mp) * 12) + max(0, 20 - (ga / mp) * 8) + \
           min(15, g_sh * 100) + min(15, g_sot * 40) + min(10, sot_pct / 5)
    if poss > 40:
        puan += min(5, (poss - 40) / 4)
    return min(100, puan)


def build_sezon_dict(tv):
    if not tv:
        return {
            'MP': 0, 'mp': 0, 'Gls': 0, 'gls': 0, 'Ast': 0, 'ast': 0,
            'CrdY': 0, 'crdy': 0, 'CrdR': 0, 'crdr': 0, 'Keeper_GA': 0, 'keeper_ga': 0,
            'Gls_pm': 0.0, 'gls_pm': 0.0, 'Sh': 0, 'sh': 0, 'SoT': 0, 'sot': 0,
            'Sh_pm': 0.0, 'sh_pm': 0.0, 'SoT_pm': 0.0, 'sot_pm': 0.0,
            'Keeper_GA_pm': 0.0, 'SoT_pct': 0.0, 'G_per_Sh': 0.0, 'G_per_SoT': 0.0, 'Poss': 0.0
        }

    mp = _tv_get(tv, 'MP')
    gls = _tv_get(tv, 'Gls')
    ast = _tv_get(tv, 'Ast')
    crdy = _tv_get(tv, 'CrdY')
    crdr = _tv_get(tv, 'CrdR')
    ga = _tv_get(tv, 'Keeper_GA')
    sh = _tv_get(tv, 'Sh')
    sot = _tv_get(tv, 'SoT')
    poss = _tv_get(tv, 'Possession')

    mp_valid = max(1.0, mp)
    gls_pm = round(gls / mp_valid, 2)
    sh_pm = round(sh / mp_valid, 2)
    sot_pm = round(sot / mp_valid, 2)
    ga_pm = round(ga / mp_valid, 2)

    return {
        'MP': int(mp), 'mp': int(mp),
        'Gls': int(gls), 'gls': int(gls),
        'Ast': int(ast), 'ast': int(ast),
        'CrdY': int(crdy), 'crdy': int(crdy),
        'CrdR': int(crdr), 'crdr': int(crdr),
        'Keeper_GA': int(ga), 'keeper_ga': int(ga),
        'Gls_pm': gls_pm, 'gls_pm': gls_pm,
        'Sh': int(sh), 'sh': int(sh),
        'SoT': int(sot), 'sot': int(sot),
        'Sh_pm': sh_pm, 'sh_pm': sh_pm,
        'SoT_pm': sot_pm, 'sot_pm': sot_pm,
        'Keeper_GA_pm': ga_pm,
        'SoT_pct': round((sot / sh * 100), 1) if sh > 0 else 0.0,
        'G_per_Sh': round((gls / sh * 100), 2) if sh > 0 else 0.0,
        'G_per_SoT': round((gls / sot * 100), 2) if sot > 0 else 0.0,
        'Poss': round(poss, 1)
    }


def genel_istatistikler(takim_key, sezon=None):
    empty_genel = build_sezon_dict({})
    empty_genel.update({
        'sezon_sayisi': 0, 'sezonlar': [],
        'ilk_sezon': '-', 'son_sezon': '-',
        'toplam_mp': 0, 'toplam_gls': 0,
        'toplam_sh': 0, 'toplam_sot': 0, 'toplam_ga': 0
    })

    if takimlar.empty or '_key_squad' not in takimlar.columns:
        return empty_genel

    t_veriler = takimlar[match_team_key(takimlar['_key_squad'], takim_key)].copy()
    if len(t_veriler) == 0:
        return empty_genel

    if sezon is not None and 'Sezon' in t_veriler.columns:
        t_veriler = t_veriler[t_veriler['Sezon'] == sezon]
        if len(t_veriler) == 0:
            return empty_genel

    toplamlar = {}
    for col in ['mp', 'gls', 'ast', 'crdy', 'crdr', 'sh', 'sot', 'keeper_ga', 'pk', 'pkatt', 'g_a']:
        if col in t_veriler.columns:
            toplamlar[col] = pd.to_numeric(t_veriler[col], errors='coerce').fillna(0).sum()
        else:
            toplamlar[col] = 0
    if 'possession' in t_veriler.columns:
        toplamlar['possession'] = pd.to_numeric(t_veriler['possession'], errors='coerce').mean()
    else:
        toplamlar['possession'] = 0

    res = build_sezon_dict(toplamlar)
    sezonlar = sorted(t_veriler['Sezon'].dropna().unique()) if 'Sezon' in t_veriler.columns else []
    res.update({
        'sezon_sayisi': len(sezonlar),
        'sezonlar': sezonlar,
        'ilk_sezon': sezonlar[0] if sezonlar else '-',
        'son_sezon': sezonlar[-1] if sezonlar else '-',
        'toplam_mp': res['MP'],
        'toplam_gls': res['Gls'],
        'toplam_sh': res['Sh'],
        'toplam_sot': res['SoT'],
        'toplam_ga': res['Keeper_GA']
    })
    return res


def _empty_saha():
    return {
        'mac': 0, 'galibiyet': 0, 'beraberlik': 0, 'maglubiyet': 0,
        'galibiyet_yuzde': 0, 'beraberlik_yuzde': 0, 'maglubiyet_yuzde': 0,
        'atilan_gol': 0, 'yenen_gol': 0, 'gol_pm': 0.0, 'yenen_gol_pm': 0.0,
        'toplam_gol_pm': 0.0, 'son5': []
    }


def ic_saha_performansi(takim_key, lig):
    if maclar.empty or '_key_home' not in maclar.columns:
        return _empty_saha()

    m = maclar[
        match_team_key(maclar['_key_home'], takim_key) &
        (maclar['Lig'] == lig) &
        (maclar['Sezon'] == GUNCEL_SEZON)
    ].copy()
    if len(m) == 0:
        return _empty_saha()

    if 'Date' in m.columns:
        m = m.sort_values('Date', ascending=False)

    son5 = [{
        'tarih': r['Date'].strftime('%d.%m.%Y') if pd.notnull(r.get('Date')) else '',
        'rakim': r.get('Away_Display', r.get('Away', '')),
        'skor': f"{int(r['HomeGoals'])}-{int(r['AwayGoals'])}",
        'kazandi': bool(r['HomeGoals'] > r['AwayGoals']),
        'berabere': bool(r['HomeGoals'] == r['AwayGoals'])
    } for _, r in m.head(5).iterrows()]

    n = len(m)
    g = int((m['HomeGoals'] > m['AwayGoals']).sum())
    b = int((m['HomeGoals'] == m['AwayGoals']).sum())
    mag = int((m['HomeGoals'] < m['AwayGoals']).sum())

    return {
        'mac': n, 'galibiyet': g, 'beraberlik': b, 'maglubiyet': mag,
        'galibiyet_yuzde': round((g / n) * 100) if n > 0 else 0,
        'beraberlik_yuzde': round((b / n) * 100) if n > 0 else 0,
        'maglubiyet_yuzde': round((mag / n) * 100) if n > 0 else 0,
        'atilan_gol': int(m['HomeGoals'].sum()),
        'yenen_gol': int(m['AwayGoals'].sum()),
        'gol_pm': round(m['HomeGoals'].mean(), 2),
        'yenen_gol_pm': round(m['AwayGoals'].mean(), 2),
        'toplam_gol_pm': round((m['HomeGoals'] + m['AwayGoals']).mean(), 2),
        'son5': son5
    }


def dis_saha_performansi(takim_key, lig):
    if maclar.empty or '_key_away' not in maclar.columns:
        return _empty_saha()

    m = maclar[
        match_team_key(maclar['_key_away'], takim_key) &
        (maclar['Lig'] == lig) &
        (maclar['Sezon'] == GUNCEL_SEZON)
    ].copy()
    if len(m) == 0:
        return _empty_saha()

    if 'Date' in m.columns:
        m = m.sort_values('Date', ascending=False)

    son5 = [{
        'tarih': r['Date'].strftime('%d.%m.%Y') if pd.notnull(r.get('Date')) else '',
        'rakim': r.get('Home_Display', r.get('Home', '')),
        'skor': f"{int(r['HomeGoals'])}-{int(r['AwayGoals'])}",
        'kazandi': bool(r['AwayGoals'] > r['HomeGoals']),
        'berabere': bool(r['AwayGoals'] == r['HomeGoals'])
    } for _, r in m.head(5).iterrows()]

    n = len(m)
    g = int((m['AwayGoals'] > m['HomeGoals']).sum())
    b = int((m['AwayGoals'] == m['HomeGoals']).sum())
    mag = int((m['AwayGoals'] < m['HomeGoals']).sum())

    return {
        'mac': n, 'galibiyet': g, 'beraberlik': b, 'maglubiyet': mag,
        'galibiyet_yuzde': round((g / n) * 100) if n > 0 else 0,
        'beraberlik_yuzde': round((b / n) * 100) if n > 0 else 0,
        'maglubiyet_yuzde': round((mag / n) * 100) if n > 0 else 0,
        'atilan_gol': int(m['AwayGoals'].sum()),
        'yenen_gol': int(m['HomeGoals'].sum()),
        'gol_pm': round(m['AwayGoals'].mean(), 2),
        'yenen_gol_pm': round(m['HomeGoals'].mean(), 2),
        'toplam_gol_pm': round((m['HomeGoals'] + m['AwayGoals']).mean(), 2),
        'son5': son5
    }


# ============================================
# ANA ANALİZ
# ============================================
def analiz_et(ev_adi, dep_adi, lig):
    ev_goster = get_canonical_name(ev_adi)
    dep_goster = get_canonical_name(dep_adi)
    ev = normalize_key(ev_adi)
    dep = normalize_key(dep_adi)

    empty_sezon = build_sezon_dict({})

    sonuc = {
        'ev': ev_goster, 'dep': dep_goster, 'lig': lig,
        'h2h': None, 'h2h_stats': None,
        'ev_sezon': empty_sezon, 'dep_sezon': empty_sezon,
        'ev_genel': genel_istatistikler(ev),
        'dep_genel': genel_istatistikler(dep),
        'ev_ic_saha': ic_saha_performansi(ev, lig),
        'dep_dis_saha': dis_saha_performansi(dep, lig),
        'ev_profil': None, 'dep_profil': None,
        'ev_guc': 0, 'dep_guc': 0,
        'tahmin': {}, 'hata': None,
        'veri_kaynagi': 'Supabase Veritabanı'
    }

    # H2H — tüm sezonlar
    h2h = pd.DataFrame()
    if not maclar.empty and {'_key_home', '_key_away'}.issubset(maclar.columns):
        h2h = maclar[
            ((maclar['_key_home'] == ev) & (maclar['_key_away'] == dep)) |
            ((maclar['_key_home'] == dep) & (maclar['_key_away'] == ev))
        ]
        if 'Date' in h2h.columns:
            h2h = h2h.sort_values('Date', ascending=False)
        h2h = h2h.head(10)

    if len(h2h) > 0:
        h2h_list = []
        ev_g = dep_g = ber = top_gol = btts = ust = 0
        for _, m in h2h.iterrows():
            eg, dg = int(m['HomeGoals']), int(m['AwayGoals'])
            top_gol += eg + dg
            if eg == dg:
                ber += 1; s = "Beraberlik"
            elif (m['_key_home'] == ev and eg > dg) or (m['_key_away'] == ev and dg > eg):
                ev_g += 1; s = f"{ev_goster} kazandi"
            else:
                dep_g += 1; s = f"{dep_goster} kazandi"
            if eg > 0 and dg > 0: btts += 1
            if eg + dg > 2.5: ust += 1
            h2h_list.append({
                'tarih': m['Date'].strftime('%d.%m.%Y') if pd.notnull(m.get('Date')) else '',
                'ev': m.get('Home_Display', m.get('Home', '')),
                'dep': m.get('Away_Display', m.get('Away', '')),
                'ev_gol': eg, 'dep_gol': dg, 'sonuc': s
            })
        n = len(h2h)
        sonuc['h2h'] = h2h_list
        sonuc['h2h_stats'] = {
            'n': n, 'ev_g': ev_g, 'dep_g': dep_g, 'ber': ber,
            'ev_yuzde': round(ev_g / n * 100),
            'dep_yuzde': round(dep_g / n * 100),
            'ber_yuzde': round(ber / n * 100),
            'ort_gol': round(top_gol / n, 2),
            'btts_yuzde': round(btts / n * 100),
            'ust_25_yuzde': round(ust / n * 100)
        }

    # Bu sezon takım verisi (Güç puanı için Akıllı Sezon Yedekleme)
    ev_s = pd.DataFrame()
    dep_s = pd.DataFrame()

    if not takimlar.empty and '_key_squad' in takimlar.columns:
        t_ev = takimlar[match_team_key(takimlar['_key_squad'], ev)]
        if not t_ev.empty:
            ev_s = t_ev[t_ev['Sezon'] == GUNCEL_SEZON]
            if len(ev_s) == 0:
                en_son = t_ev['Sezon'].dropna().max()
                ev_s = t_ev[t_ev['Sezon'] == en_son]

        t_dep = takimlar[match_team_key(takimlar['_key_squad'], dep)]
        if not t_dep.empty:
            dep_s = t_dep[t_dep['Sezon'] == GUNCEL_SEZON]
            if len(dep_s) == 0:
                en_son_dep = t_dep['Sezon'].dropna().max()
                dep_s = t_dep[t_dep['Sezon'] == en_son_dep]

    if len(ev_s) > 1 and 'guncelleme' in ev_s.columns:
        ev_s = ev_s.sort_values('guncelleme', ascending=False)
    if len(dep_s) > 1 and 'guncelleme' in dep_s.columns:
        dep_s = dep_s.sort_values('guncelleme', ascending=False)

    if len(ev_s) > 0:
        ev_v = ev_s.iloc[0].to_dict()
        ev_guc = guc_puani_hesapla(ev_v)
        sonuc['ev_sezon'] = build_sezon_dict(ev_v)
    else:
        ev_guc = 50

    if len(dep_s) > 0:
        dep_v = dep_s.iloc[0].to_dict()
        dep_guc = guc_puani_hesapla(dep_v)
        sonuc['dep_sezon'] = build_sezon_dict(dep_v)
    else:
        dep_guc = 50

    sonuc['ev_guc'] = round(ev_guc, 1)
    sonuc['dep_guc'] = round(dep_guc, 1)

    ev_ic = sonuc['ev_ic_saha'].get('galibiyet_yuzde', 0)
    dep_dis = sonuc['dep_dis_saha'].get('galibiyet_yuzde', 0)

    ev_puan = ev_guc + (ev_ic * 0.3)
    dep_puan = dep_guc + (dep_dis * 0.3)
    ber_puan = 35

    top = ev_puan + dep_puan + ber_puan or 1
    ev_o = round((ev_puan / top) * 100)
    dep_o = round((dep_puan / top) * 100)
    ber_o = round((ber_puan / top) * 100)

    en_y = max(ev_o, dep_o, ber_o)
    tahmin = f"{ev_goster} KAZANIR" if ev_o == en_y else f"{dep_goster} KAZANIR" if dep_o == en_y else "BERABERLİK"

    ev_gls_pm_sezon = sonuc['ev_sezon'].get('Gls_pm', 0) or 0
    dep_gls_pm_sezon = sonuc['dep_sezon'].get('Gls_pm', 0) or 0

    if sonuc.get('h2h_stats') and sonuc['h2h_stats'].get('n', 0) >= 2:
        h2h_ort = sonuc['h2h_stats']['ort_gol']
        bek_gol = round(0.4 * h2h_ort + 0.6 * (ev_gls_pm_sezon + dep_gls_pm_sezon), 2) \
            if (ev_gls_pm_sezon + dep_gls_pm_sezon) > 0 else round(h2h_ort, 2)
        btts_oran = sonuc['h2h_stats'].get('btts_yuzde', 50) / 100.0
    else:
        bek_gol = round(ev_gls_pm_sezon + dep_gls_pm_sezon, 2) \
            if (ev_gls_pm_sezon + dep_gls_pm_sezon) > 0 else 2.5
        btts_oran = 0.7 if (ev_gls_pm_sezon > 0.8 and dep_gls_pm_sezon > 0.8) else 0.3

    if bek_gol >= 2.8:
        gol_tahmin = "2.5 Üstü"
    elif bek_gol <= 2.2:
        gol_tahmin = "2.5 Altı"
    else:
        gol_tahmin = "Belirsiz"

    if btts_oran >= 0.6:
        btts_tahmin = "Karşılıklı Gol: Var"
    elif btts_oran <= 0.4:
        btts_tahmin = "Karşılıklı Gol: Yok"
    else:
        btts_tahmin = "Belirsiz"

    sonuc['tahmin'] = {
        'ev_o': ev_o, 'dep_o': dep_o, 'ber_o': ber_o,
        'sonuc': tahmin, 'guven': en_y,
        'bek_gol': bek_gol,
        'gol': gol_tahmin,
        'btts': btts_tahmin
    }
    return sonuc


# ============================================
# FLASK ROTALARI
# ============================================
@app.route("/", methods=["GET"])
def index():
    ligler = sorted(list(LIG_TAKIMLARI.keys()))
    return render_template("index.html", ligler=ligler)

@app.route("/api/takimlar/<lig>", methods=["GET"])
def api_takimlar(lig):
    takimlar_listesi = LIG_TAKIMLARI.get(lig, [])
    return jsonify({"takimlar": takimlar_listesi})

@app.route("/analiz", methods=["POST"])
def analiz_sayfasi():
    lig = request.form.get("lig")
    ev = request.form.get("ev")
    dep = request.form.get("dep")
    
    if not lig or not ev or not dep or ev == dep:
        return "<h1>Hata: Eksik veya aynı takımları seçtiniz.</h1><a href='/'>Geri Dön</a>"
        
    s = analiz_et(ev, dep, lig)
    if not s:
        return "<h1>Analiz verisi bulunamadı.</h1><a href='/'>Geri Dön</a>"
        
    return render_template("sonuc.html", s=s)


if __name__ == "__main__":
    app.run(debug=True)
