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
        <p>Supabase veritabanı ve maç karşılaştırma sistemi hazır.</p>
        <hr style="width: 50%; margin: 20px auto;">
        <a href="/karsilastir" style="font-size: 18px; padding: 12px 24px; background: #27ae60; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">🎯 Takım Karşılaştır & Kupon Fikri Al</a>
        <br><br>
        <a href="/analiz" style="font-size: 16px; color: #2c3e50; text-decoration: none;">Genel Lig Raporunu Gör (/analiz)</a>
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

@app.route("/analiz")
def analiz():
    try:
        supabase = get_supabase_client()
        response = supabase.table("fb_takim_verileri").select("*").execute()
        data = response.data
        if not data:
            return "<h1>Henüz veri yok. Lütfen /sync çalıştırın.</h1>"
        df = pd.DataFrame(data)
        top_gol = df.sort_values(by="gls", ascending=False)[["squad", "gls", "mp", "lig"]].head(10)
        return f"""
        <html>
            <head><title>Genel Analiz</title></head>
            <body style="font-family: Arial; margin: 30px;">
                <a href="/">&larr; Ana Sayfa</a> | <a href="/karsilastir">Takım Karşılaştır & Kupon</a>
                <h1>🏆 En Çok Gol Atan Takımlar</h1>
                {top_gol.to_html(index=False, border=0, classes='table')}
            </body>
        </html>
        """
    except Exception as e:
        return f"Hata: {e}"

@app.route("/karsilastir", methods=["GET", "POST"])
def karsilastir():
    try:
        supabase = get_supabase_client()
        response = supabase.table("fb_takim_verileri").select("squad, sezon, lig, gls, ast, possession, sh, sot, mp").execute()
        data = response.data
        if not data:
            return "<h1>Supabase'de veri bulunamadı. Önce /sync çalıştırın.</h1>"
            
        df = pd.DataFrame(data)
        takimlar = sorted(df["squad"].unique().tolist())
        
        sonuc_html = ""
        secilen_t1 = request.form.get("takim1", "")
        secilen_t2 = request.form.get("takim2", "")
        
        if request.method == "POST" and secilen_t1 and secilen_t2:
            t1_row = df[df["squad"] == secilen_t1].iloc[0]
            t2_row = df[df["squad"] == secilen_t2].iloc[0]
            
            # Basit Kupon ve Skor Analizi Mantığı
            t1_gol_ort = t1_row["gls"] / max(t1_row["mp"], 1)
            t2_gol_ort = t2_row["gls"] / max(t2_row["mp"], 1)
            toplam_beklenen_gol = t1_gol_ort + t2_gol_ort
            
            tahmin = "Karşılıklı Gol Var (KG Var)" if toplam_beklenen_gol > 2.5 else "2.5 Alt / Düşük Skorlu Geçebilir"
            
            sonuc_html = f"""
            <div style="background: #eef2f3; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <h3>📊 Karşılaştırma Sonucu & Kupon Fikri</h3>
                <table style="width:100%; border-collapse:collapse; background:white;">
                    <tr><th>İstatistik</th><th>{secilen_t1}</th><th>{secilen_t2}</th></tr>
                    <tr><td>Lig</td><td>{t1_row['lig']}</td><td>{t2_row['lig']}</td></tr>
                    <tr><td>Maç Sayısı</td><td>{t1_row['mp']}</td><td>{t2_row['mp']}</td></tr>
                    <tr><td>Toplam Gol</td><td>{t1_row['gls']}</td><td>{t2_row['gls']}</td></tr>
                    <tr><td>Maç Başı Gol Ort.</td><td>{t1_gol_ort:.2f}</td><td>{t2_gol_ort:.2f}</td></tr>
                    <tr><td>Topa Sahip Olma (%)</td><td>%{t1_row['possession']}</td><td>%{t2_row['possession']}</td></tr>
                    <tr><td>Şut / Kaleyi Bulan Şut</td><td>{t1_row['sh']} / {t1_row['sot']}</td><td>{t2_row['sh']} / {t2_row['sot']}</td></tr>
                </table>
                <div style="margin-top: 20px; padding: 15px; background: #d4edda; color: #155724; border-radius: 5px; font-weight: bold;">
                    💡 Kupon Tavsiyesi / Yapay Zeka Önerisi: {tahmin} (Beklenen Maç Gol Skoru Toplamı: {toplam_beklenen_gol:.2f})
                </div>
            </div>
            """

        options_html = "".join([f'<option value="{t}" {"selected" if t == secilen_t1 else ""}>{t}</option>' for t in takimlar])
        options_html2 = "".join([f'<option value="{t}" {"selected" if t == secilen_t2 else ""}>{t}</option>' for t in takimlar])

        html = f"""
        <html>
            <head>
                <title>Takım Karşılaştırma & Kupon Fikri</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 30px; background: #f9f9fb; color: #333; }}
                    .container {{ max-width: 800px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                    select, button {{ padding: 10px; font-size: 16px; margin: 10px 0; width: 100%; border-radius: 5px; border: 1px solid #ccc; }}
                    button {{ background: #27ae60; color: white; font-weight: bold; cursor: pointer; }}
                    button:hover {{ background: #219653; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
                    th {{ background: #2c3e50; color: white; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <a href="/">&larr; Ana Sayfaya Dön</a>
                    <h2>⚽ İki Takım Karşılaştırma ve Kupon Asistanı</h2>
                    <form method="POST">
                        <label><b>1. Takımı Seçin:</b></label>
                        <select name="takim1">{options_html}</select>
                        
                        <label><b>2. Takımı Seçin:</b></label>
                        <select name="takim2">{options_html2}</select>
                        
                        <button type="submit">Karşılaştır ve Kupon Fikri Ver</button>
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