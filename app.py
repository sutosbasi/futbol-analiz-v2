import os
import pandas as pd
import unicodedata
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = Flask(__name__)

# ============================================
# 1. SUPABASE BAĞLANTISI VE VERİ YÜKLEME
# ============================================
def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key: return None
    return create_client(url, key)

def verileri_yukle():
    supabase = get_supabase_client()
    if not supabase: return pd.DataFrame(), pd.DataFrame()
    try:
        resp_takim = supabase.table("fb_takim_verileri").select("*").execute()
        takimlar = pd.DataFrame(resp_takim.data) if resp_takim.data else pd.DataFrame()
        
        resp_mac = supabase.table("fb_maclar").select("*").execute()
        maclar = pd.DataFrame(resp_mac.data) if resp_mac.data else pd.DataFrame()
        
        if not maclar.empty:
            renames = {
                'tarih': 'Date',
                'ev': 'Home',
                'dep': 'Away',
                'ev_gol': 'HomeGoals',
                'dep_gol': 'AwayGoals',
                'sezon': 'Sezon',
                'lig': 'Lig'
            }
            maclar = maclar.rename(columns=renames)
            
        return takimlar, maclar
    except Exception as e:
        print(f"Veri yükleme hatası: {e}")
        return pd.DataFrame(), pd.DataFrame()

takimlar, maclar = verileri_yukle()

# ============================================
# 2. NORMALİZASYON VE LİSTELEME
# ============================================
ALIAS = {
    'tottenham hotspur': 'tottenham', 'manchester city': 'man city',
    'manchester united': 'man united', 'manchester utd': 'man united',
    'wolverhampton wanderers': 'wolves', 'wolverhampton': 'wolves',
    'brighton & hove albion': 'brighton', 'brighton and hove albion': 'brighton',
    'nottingham forest': 'nottm forest', "nott'm forest": 'nottm forest',
    'sheffield united': 'sheffield utd', 'west bromwich albion': 'west brom',
    'newcastle united': 'newcastle', 'leeds united': 'leeds',
    'west ham united': 'west ham', 'norwich city': 'norwich',
}

def normalize_takim(t):
    if pd.isna(t): return ''
    t = str(t).strip().lower()
    for tr, en in [('ı','i'),('İ','i'),('ş','s'),('ğ','g'),('ü','u'),('ö','o'),('ç','c')]:
        t = t.replace(tr, en)
    t = t.replace('istanbul basaksehir', 'basaksehir')
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    return ALIAS.get(t, t)

if not takimlar.empty:
    takimlar.columns = [c.lower() for c in takimlar.columns]
    if 'squad' in takimlar.columns:
        takimlar['_key_squad'] = takimlar['squad'].apply(normalize_takim)

if not maclar.empty:
    if 'Home' in maclar.columns: maclar['_key_home'] = maclar['Home'].apply(normalize_takim)
    if 'Away' in maclar.columns: maclar['_key_away'] = maclar['Away'].apply(normalize_takim)
    if 'Date' in maclar.columns: maclar['Date'] = pd.to_datetime(maclar['Date'], errors='coerce')

LIG_TAKIMLARI = {}
if not takimlar.empty and 'lig' in takimlar.columns and 'squad' in takimlar.columns:
    for lig in sorted(takimlar['lig'].dropna().unique()):
        lt = takimlar[takimlar['lig'] == lig]
        LIG_TAKIMLARI[lig] = sorted(lt['squad'].unique().tolist())

# ============================================
# 3. İSTATİSTİK VE ANALİZ MOTORU (GÜVENLİ NAN KONTROLÜ)
# ============================================
def guc_puani_hesapla(tv):
    mp = float(tv.get('mp', 1) or 1)
    if pd.isna(mp) or mp <= 0: mp = 1.0
    
    gls = float(tv.get('gls', 0) or 0)
    if pd.isna(gls): gls = 0.0
    
    ga = float(tv.get('keeper_ga', 0) or 0)
    if pd.isna(ga): ga = 0.0
    
    g_sh = float(tv.get('g_per_sh', 0) or 0)
    if pd.isna(g_sh): g_sh = 0.0
    
    sot_pct = float(tv.get('sot_pct', 0) or 0)
    if pd.isna(sot_pct): sot_pct = 0.0
    
    poss = float(tv.get('possession', tv.get('poss', 50)) or 50)
    if pd.isna(poss): poss = 50.0
    
    gls_pm = gls / mp
    ga_pm = ga / mp
    puan = 0
    puan += min(30, gls_pm * 12)
    puan += max(0, 20 - ga_pm * 8)
    puan += min(20, g_sh * 100)
    puan += min(15, sot_pct / 5)
    puan += min(15, (poss - 40) / 2) if poss > 40 else 0
    return min(100, max(10, puan))

def ic_saha_performansi(takim_adi, lig):
    if maclar.empty or 'Home' not in maclar.columns: return None
    t_key = normalize_takim(takim_adi)
    m = maclar[(maclar['_key_home'] == t_key) & (maclar['Lig'] == lig)].copy()
    if len(m) == 0: m = maclar[maclar['_key_home'] == t_key].copy()
    if len(m) == 0: return None
    
    m = m.sort_values('Date', ascending=False).head(5)
    hg = m['HomeGoals'].astype(float)
    ag = m['AwayGoals'].astype(float)
    
    gal = int((hg > ag).sum())
    ber = int((hg == ag).sum())
    mag = int((hg < ag).sum())
    toplam = len(m)
    
    son5_liste = []
    for _, row in m.iterrows():
        th = int(row['HomeGoals']) if pd.notnull(row['HomeGoals']) else 0
        ta = int(row['AwayGoals']) if pd.notnull(row['AwayGoals']) else 0
        son5_liste.append({
            'tarih': row['Date'].strftime('%d.%m.%Y') if pd.notnull(row['Date']) else '-',
            'rakim': row['Away'],
            'skor': f"{th} - {ta}",
            'kazandi': th > ta,
            'berabere': th == ta
        })
        
    return {
        'mac': toplam, 'galibiyet': gal, 'galibiyet_yuzde': round(gal / toplam * 100) if toplam > 0 else 0,
        'beraberlik': ber, 'beraberlik_yuzde': round(ber / toplam * 100) if toplam > 0 else 0,
        'maglubiyet': mag, 'maglubiyet_yuzde': round(mag / toplam * 100) if toplam > 0 else 0,
        'atilan_gol': int(hg.sum()), 'yenen_gol': int(ag.sum()),
        'gol_pm': round(hg.sum() / toplam, 2) if toplam > 0 else 0,
        'yenen_gol_pm': round(ag.sum() / toplam, 2) if toplam > 0 else 0,
        'toplam_gol_pm': round((hg.sum() + ag.sum()) / toplam, 2) if toplam > 0 else 0,
        'son5': son5_liste
    }

def dis_saha_performansi(takim_adi, lig):
    if maclar.empty or 'Away' not in maclar.columns: return None
    t_key = normalize_takim(takim_adi)
    m = maclar[(maclar['_key_away'] == t_key) & (maclar['Lig'] == lig)].copy()
    if len(m) == 0: m = maclar[maclar['_key_away'] == t_key].copy()
    if len(m) == 0: return None
    
    m = m.sort_values('Date', ascending=False).head(5)
    hg = m['HomeGoals'].astype(float)
    ag = m['AwayGoals'].astype(float)
    
    gal = int((ag > hg).sum())
    ber = int((ag == hg).sum())
    mag = int((ag < hg).sum())
    toplam = len(m)
    
    son5_liste = []
    for _, row in m.iterrows():
        th = int(row['HomeGoals']) if pd.notnull(row['HomeGoals']) else 0
        ta = int(row['AwayGoals']) if pd.notnull(row['AwayGoals']) else 0
        son5_liste.append({
            'tarih': row['Date'].strftime('%d.%m.%Y') if pd.notnull(row['Date']) else '-',
            'rakim': row['Home'],
            'skor': f"{ta} - {th}",
            'kazandi': ta > th,
            'berabere': ta == th
        })
        
    return {
        'mac': toplam, 'galibiyet': gal, 'galibiyet_yuzde': round(gal / toplam * 100) if toplam > 0 else 0,
        'beraberlik': ber, 'beraberlik_yuzde': round(ber / toplam * 100) if toplam > 0 else 0,
        'maglubiyet': mag, 'maglubiyet_yuzde': round(mag / toplam * 100) if toplam > 0 else 0,
        'atilan_gol': int(ag.sum()), 'yenen_gol': int(hg.sum()),
        'gol_pm': round(ag.sum() / toplam, 2) if toplam > 0 else 0,
        'yenen_gol_pm': round(hg.sum() / toplam, 2) if toplam > 0 else 0,
        'toplam_gol_pm': round((ag.sum() + hg.sum()) / toplam, 2) if toplam > 0 else 0,
        'son5': son5_liste
    }

def takim_sezon_istatistikleri(takim_adi):
    t = takimlar[takimlar['squad'] == takim_adi]
    if t.empty: return None
    row = t.iloc[-1]
    
    mp = float(row.get('mp', 1) or 1)
    if pd.isna(mp) or mp <= 0: mp = 1.0
    
    gls = float(row.get('gls', 0) or 0)
    if pd.isna(gls): gls = 0.0
    
    sh = float(row.get('sh', 0) or 0)
    if pd.isna(sh): sh = 0.0
    
    sot = float(row.get('sot', 0) or 0)
    if pd.isna(sot): sot = 0.0
    
    sot_pct = float(row.get('sot_pct', 0) or 0)
    if pd.isna(sot_pct): sot_pct = 0.0
    
    poss = float(row.get('possession', row.get('poss', 50)) or 50)
    if pd.isna(poss): poss = 50.0
    
    keeper_ga = float(row.get('keeper_ga', 0) or 0)
    if pd.isna(keeper_ga): keeper_ga = 0.0
    
    g_per_sh = float(row.get('g_per_sh', 0) or 0)
    if pd.isna(g_per_sh): g_per_sh = 0.0
    g_per_sh *= 100
    
    g_per_sot = float(row.get('g_per_sot', 0) or 0)
    if pd.isna(g_per_sot): g_per_sot = 0.0
    g_per_sot *= 100
    
    return {
        'MP': int(mp), 'Gls': int(gls), 'Keeper_GA': int(keeper_ga),
        'Gls_pm': round(gls / mp, 2) if mp > 0 else 0,
        'Sh': int(sh), 'Sh_pm': round(sh / mp, 1) if mp > 0 else 0,
        'SoT': int(sot), 'SoT_pm': round(sot / mp, 1) if mp > 0 else 0,
        'SoT_pct': round(sot_pct, 1), 'G_per_Sh': round(g_per_sh, 1),
        'G_per_SoT': round(g_per_sot, 1), 'Poss': round(poss, 1)
    }

def genel_istatistikler(takim_adi):
    t_veriler = takimlar[takimlar['squad'] == takim_adi]
    if t_veriler.empty: return None
    
    sezon_sayisi = len(t_veriler)
    top_mp = float(t_veriler['mp'].astype(float).sum() or 0)
    top_gls = float(t_veriler['gls'].astype(float).sum() or 0)
    top_ga = float(t_veriler['keeper_ga'].astype(float).sum() or 0) if 'keeper_ga' in t_veriler.columns else 0.0
    top_sh = float(t_veriler['sh'].astype(float).sum() or 0)
    top_sot = float(t_veriler['sot'].astype(float).sum() or 0)
    
    poss_val = t_veriler['possession'] if 'possession' in t_veriler.columns else t_veriler.get('poss', pd.Series([50]))
    poss_ort = float(poss_val.astype(float).mean() or 50.0)
    sot_pct = float(t_veriler['sot_pct'].astype(float).mean() or 0.0)
    
    g_per_sot = round((top_gls / top_sot * 100), 1) if top_sot > 0 else 0.0
    
    sezonlar = sorted(t_veriler['sezon'].dropna().unique()) if 'sezon' in t_veriler.columns else []
    ilk_sezon = sezonlar[0] if sezonlar else "Geçmiş Sezonlar"
    son_sezon = sezonlar[-1] if sezonlar else "Güncel Sezon"

    return {
        'sezon_sayisi': sezon_sayisi,
        'ilk_sezon': ilk_sezon,
        'son_sezon': son_sezon,
        'toplam_mp': int(top_mp),
        'toplam_gls': int(top_gls),
        'toplam_ga': int(top_ga),
        'toplam_sh': int(top_sh),
        'toplam_sot': int(top_sot),
        'Gls_pm': round(top_gls / top_mp, 2) if top_mp > 0 else 0,
        'Keeper_GA_pm': round(top_ga / top_mp, 2) if top_mp > 0 else 0,
        'Sh_pm': round(top_sh / top_mp, 1) if top_mp > 0 else 0,
        'SoT_pm': round(top_sot / top_mp, 1) if top_mp > 0 else 0,
        'SoT_pct': round(sot_pct, 1),
        'G_per_SoT': g_per_sot,
        'Poss': round(poss_ort, 1)
    }

def analiz_et(ev_adi, dep_adi, lig):
    if takimlar.empty: return None
    
    ev_row = takimlar[(takimlar['lig'] == lig) & (takimlar['squad'] == ev_adi)]
    dep_row = takimlar[(takimlar['lig'] == lig) & (takimlar['squad'] == dep_adi)]
    
    if ev_row.empty or dep_row.empty: return None
        
    t1 = ev_row.iloc[-1]
    t2 = dep_row.iloc[-1]
    
    ev_guc = guc_puani_hesapla(t1)
    dep_guc = guc_puani_hesapla(t2)
    
    t1_mp = max(float(t1.get('mp', 1) or 1), 1)
    t2_mp = max(float(t2.get('mp', 1) or 1), 1)
    
    ev_g_ort = float(t1.get('gls', 0) or 0) / t1_mp
    dep_g_ort = float(t2.get('gls', 0) or 0) / t2_mp
    toplam_beklenen_gol = ev_g_ort + dep_g_ort
    
    h2h_stats = None
    h2h_maclar = []
    ev_key, dep_key = normalize_takim(ev_adi), normalize_takim(dep_adi)
    if not maclar.empty and '_key_home' in maclar.columns:
        h2h = maclar[((maclar['_key_home']==ev_key) & (maclar['_key_away']==dep_key)) |
                     ((maclar['_key_home']==dep_key) & (maclar['_key_away']==ev_key))]
        h2h = h2h.sort_values('Date', ascending=False).head(10)
        n = len(h2h)
        if n > 0:
            ev_g = dep_g = ber = top_gol = 0
            for _, m in h2h.iterrows():
                hg = float(m['HomeGoals']) if pd.notnull(m['HomeGoals']) else 0.0
                ag = float(m['AwayGoals']) if pd.notnull(m['AwayGoals']) else 0.0
                top_gol += hg + ag
                
                if hg == ag: 
                    ber += 1
                    sonuc_str = "Berabere"
                elif (m['_key_home']==ev_key and hg > ag) or (m['_key_away']==ev_key and ag > hg): 
                    ev_g += 1
                    sonuc_str = f"{ev_adi} Kazandı"
                else: 
                    dep_g += 1
                    sonuc_str = f"{dep_adi} Kazandı"
                
                h2h_maclar.append({
                    'tarih': m['Date'].strftime('%d.%m.%Y') if pd.notnull(m['Date']) else '-',
                    'ev': m['Home'], 'dep': m['Away'],
                    'ev_gol': int(hg), 'dep_gol': int(ag),
                    'sonuc': sonuc_str
                })
                
            h2h_stats = {
                'n': n,
                'ev_yuzde': round(ev_g/n*100),
                'dep_yuzde': round(dep_g/n*100),
                'ber_yuzde': round(ber/n*100),
                'ort_gol': round(top_gol/n, 2)
            }

    if ev_guc > dep_guc + 5:
        sonuc = f"{ev_adi} KAZANIR"
        guven = int(50 + (ev_guc - dep_guc))
        ev_o, ber_o, dep_o = 60, 20, 20
    elif dep_guc > ev_guc + 5:
        sonuc = f"{dep_adi} KAZANIR"
        guven = int(50 + (dep_guc - ev_guc))
        ev_o, ber_o, dep_o = 20, 20, 60
    else:
        sonuc = "BERABERLİK ADAYI"
        guven = 55
        ev_o, ber_o, dep_o = 35, 30, 35

    if toplam_beklenen_gol > 2.8:
        gol_tahmin = "2.5 Üstü"
        btts = "Karşılıklı Gol: Var"
    elif toplam_beklenen_gol > 2.2:
        gol_tahmin = "1.5 Üstü / Sınırda"
        btts = "Karşılıklı Gol: Muhtemel"
    else:
        gol_tahmin = "2.5 Altı"
        btts = "Karşılıklı Gol: Yok"

    return {
        'ev': ev_adi, 'dep': dep_adi, 'lig': lig,
        'ev_guc': round(ev_guc, 1), 'dep_guc': round(dep_guc, 1),
        'ev_sezon': takim_sezon_istatistikleri(ev_adi),
        'dep_sezon': takim_sezon_istatistikleri(dep_adi),
        'ev_genel': genel_istatistikler(ev_adi),
        'dep_genel': genel_istatistikler(dep_adi),
        'ev_ic_saha': ic_saha_performansi(ev_adi, lig),
        'dep_dis_saha': dis_saha_performansi(dep_adi, lig),
        'h2h': h2h_maclar,
        'h2h_stats': h2h_stats,
        'tahmin': {
            'sonuc': sonuc, 'guven': min(95, guven),
            'ev_o': ev_o, 'ber_o': ber_o, 'dep_o': dep_o,
            'bek_gol': round(toplam_beklenen_gol, 2),
            'gol': gol_tahmin, 'btts': btts
        }
    }

# ============================================
# 4. FLASK ROTALARI
# ============================================
@app.route("/", methods=["GET"])
def index():
    ligler = sorted(list(LIG_TAKIMLARI.keys()))
    return render_template("index.html", ligler=ligler)

@app.route("/api/takimlar/<lig>", methods=["GET"])
def api_takimlar(lig):
    takimlar = LIG_TAKIMLARI.get(lig, [])
    return jsonify({"takimlar": takimlar})

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
