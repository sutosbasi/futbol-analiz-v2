import os
import pandas as pd
from flask import Flask, request
from islemci import verileri_isle_ve_yukle
from supabase_client import get_supabase_client

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <div style="font-family: Arial; text-align: center; margin-top: 50px;">
        <h1>⚽ Futbol Analiz & Kupon Asistanı Aktif</h1>
        <p>Supabase veritabanı ve detaylı karşılaştırma sistemi hazır.</p>
        <hr style="width: 50%; margin: 20px auto;">
        <a href="/karsilastir" style="font-size: 18px; padding: 12px 24px; background: #27ae60; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">🎯 Lig Seç & Detaylı Karşılaştır</a>
        <br><br>
        <a href="/sync" style="font-size: 14px; color: #3498db; text-decoration: none;">Verileri Şimdi Senkronize Et (/sync)</a>
    </div>
    """

@app.route("/sync")
def sync():
    success = verileri_isle_ve_yukle()
    if success:
        return {"durum": "başarılı", "mesaj": "Veriler başarıyla işlendi ve Supabase'e aktarıldı."}
    else:
        return {"durum": "hata", "mesaj": "Veriler işlenirken bir sorun oluştu."}, 500

@app.route("/karsilastir", methods=["GET", "POST"])
def karsilastir():
    try:
        supabase = get_supabase_client()
        # Tüm detaylı sütunları çekiyoruz
        response = supabase.table("fb_takim_verileri").select("*").execute()
        data = response.data
        if not data:
            return "<h1>Supabase'de veri bulunamadı. Önce /sync çalıştırın.</h1>"
            
        df = pd.DataFrame(data)
        ligler = sorted(df["lig"].dropna().unique().tolist())
        
        secilen_lig = request.form.get("lig", ligler[0] if ligler else "")
        df_lig = df[df["lig"] == secilen_lig] if secilen_lig else df
        takimlar = sorted(df_lig["squad"].unique().tolist())
        
        sonuc_html = ""
        secilen_t1 = request.form.get("takim1", "")
        secilen_t2 = request.form.get("takim2", "")
        
        if request.method == "POST" and secilen_t1 and secilen_t2:
            t1_row = df[df["squad"] == secilen_t1].iloc[0]
            t2_row = df[df["squad"] == secilen_t2].iloc[0]
            
            # Gelişmiş Kupon ve Skor Analizi Mantığı
            t1_mp = max(float(t1_row.get("mp", 1)), 1)
            t2_mp = max(float(t2_row.get("mp", 1)), 1)
            
            t1_gls = float(t1_row.get("gls", 0))
            t2_gls = float(t2_row.get("gls", 0))
            
            t1_gol_ort = t1_gls / t1_mp
            t2_gol_ort = t2_gls / t2_mp
            toplam_beklenen_gol = t1_gol_ort + t2_gol_ort
            
            # Kupon tahmini üretme
            if toplam_beklenen_gol > 2.8:
                tahmin = "🔥 2.5 ÜST ve Karşılıklı Gol Var (KG Var)"
            elif toplam_beklenen_gol > 2.2:
                tahmin = "⚡ Maç Geneli Gollü Geçebilir (KG Var / 1.5 Üst)"
            else:
                tahmin = "🔒 2.5 ALT / Düşük Skorlu Mücadele"

            sonuc_html = f"""
            <div style="background: #ffffff; padding: 25px; border-radius: 12px; margin-top: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
                <h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">📊 {secilen_t1} vs {secilen_t2} Detaylı Karşılaştırma Raporu</h3>
                <table style="width:100%; border-collapse:collapse; margin-top: 15px; font-size: 14px;">
                    <tr style="background: #f8f9fa;"><th style="padding: 10px; border: 1px solid #ddd;">İstatistik Kalemi</th><th style="padding: 10px; border: 1px solid #ddd; color: #e74c3c;">{secilen_t1}</th><th style="padding: 10px; border: 1px solid #ddd; color: #2980b9;">{secilen_t2}</th></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Sezon / Lig</b></td><td style="padding: 8px; border: 1px solid #ddd;">{t1_row.get('sezon')} / {t1_row.get('lig')}</td><td style="padding: 8px; border: 1px solid #ddd;">{t2_row.get('sezon')} / {t2_row.get('lig')}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Oynanan Maç (MP)</b></td><td style="padding: 8px; border: 1px solid #ddd;">{t1_row.get('mp')}</td><td style="padding: 8px; border: 1px solid #ddd;">{t2_row.get('mp')}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Atılan Gol / Asist</b></td><td style="padding: 8px; border: 1px solid #ddd;">{t1_row.get('gls')} / {t1_row.get('ast')}</td><td style="padding: 8px; border: 1px solid #ddd;">{t2_row.get('gls')} / {t2_row.get('ast')}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Maç Başı Gol Ort.</b></td><td style="padding: 8px; border: 1px solid #ddd;">{t1_gol_ort:.2f}</td><td style="padding: 8px; border: 1px solid #ddd;">{t2_gol_ort:.2f}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Topa Sahip Olma (%)</b></td><td style="padding: 8px; border: 1px solid #ddd;">%{t1_row.get('possession')}</td><td style="padding: 8px; border: 1px solid #ddd;">%{t2_row.get('possession')}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Toplam Şut / Kaleyi Bulan (SoT)</b></td><td style="padding: 8px; border: 1px solid #ddd;">{t1_row.get('sh')} / {t1_row.get('sot')}</td><td style="padding: 8px; border: 1px solid #ddd;">{t2_row.get('sh')} / {t2_row.get('sot')}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Şut Verimliliği (Gol/Şut)</b></td><td style="padding: 8px; border: 1px solid #ddd;">{float(t1_row.get('g_per_sh', 0)):.3f}</td><td style="padding: 8px; border: 1px solid #ddd;">{float(t2_row.get('g_per_sh', 0)):.3f}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Yenilen Gol (Kaleci GA)</b></td><td style="padding: 8px; border: 1px solid #ddd;">{t1_row.get('keeper_ga')}</td><td style="padding: 8px; border: 1px solid #ddd;">{t2_row.get('keeper_ga')}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Sarı / Kırmızı Kart</b></td><td style="padding: 8px; border: 1px solid #ddd;">{t1_row.get('crdy')} / {t1_row.get('crdr')}</td><td style="padding: 8px; border: 1px solid #ddd;">{t2_row.get('crdy')} / {t2_row.get('crdr')}</td></tr>
                </table>
                <div style="margin-top: 20px; padding: 15px; background: #e8f8f5; color: #117a65; border-left: 5px solid #1abc9c; border-radius: 4px; font-weight: bold; font-size: 16px;">
                    💡 Kupon Asistanı Önerisi: {tahmin} <br><span style="font-size: 13px; font-weight: normal; color: #555;">(İki takımın maç başı ortalamalarına göre beklenen toplam gol skoru: {toplam_beklenen_gol:.2f})</span>
                </div>
            </div>
            """

        lig_options = "".join([f'<option value="{l}" {"selected" if l == secilen_lig else ""}>{l}</option>' for l in ligler])
        takim_options1 = "".join([f'<option value="{t}" {"selected" if t == secilen_t1 else ""}>{t}</option>' for t in takimlar])
        takim_options2 = "".join([f'<option value="{t}" {"selected" if t == secilen_t2 else ""}>{t}</option>' for t in takimlar])

        html = f"""
        <html>
            <head>
                <title>Detaylı Takım Karşılaştırma & Kupon Asistanı</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 30px; background: #f4f6f9; color: #333; }}
                    .container {{ max-width: 900px; margin: auto; background: white; padding: 35px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
                    select, button {{ padding: 12px; font-size: 15px; margin: 8px 0 15px 0; width: 100%; border-radius: 6px; border: 1px solid #ccc; box-sizing: border-box; }}
                    button {{ background: #27ae60; color: white; font-weight: bold; cursor: pointer; transition: background 0.2s; }}
                    button:hover {{ background: #219653; }}
                    label {{ font-weight: bold; color: #2c3e50; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <a href="/" style="text-decoration: none; color: #3498db; font-weight: bold;">&larr; Ana Sayfaya Dön</a>
                    <h2 style="color: #2c3e50; margin-top: 15px;">⚽ Gelişmiş Takım Karşılaştırma & Kupon Asistanı</h2>
                    <form method="POST">
                        <label>1. Lig Filtresi Seçin:</label>
                        <select name="lig" onchange="this.form.submit()">{lig_options}</select>
                        
                        <label>2. Takım (Ev Sahibi / 1):</label>
                        <select name="takim1">{takim_options1}</select>
                        
                        <label>3. Takım (Deplasman / 2):</label>
                        <select name="takim2">{takim_options2}</select>
                        
                        <button type="submit">İstatistikleri Kıyasla ve Kupon Fikri Üret</button>
                    </form>
                    {sonuc_html}
                </div>
            </body>
        </html>
        """
        return html
    except Exception as e:
        return f"<h1>Hata Oluştu:</h1><p>{str(e)}</p>"

if __name__ == "__main__":
    app.run(debug=True)