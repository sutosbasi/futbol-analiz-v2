import os
import pandas as pd
from flask import Flask
from islemci import verileri_isle_ve_yukle
from supabase_client import get_supabase_client

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <div style="font-family: Arial; text-align: center; margin-top: 50px;">
        <h1>⚽ Futbol Analiz V2 Sistemi Aktif</h1>
        <p>Supabase senkronizasyonu hazır ve çalışır durumda.</p>
        <hr style="width: 50%; margin: 20px auto;">
        <a href="/analiz" style="font-size: 18px; padding: 10px 20px; background: #2c3e50; color: white; text-decoration: none; border-radius: 5px;">Canlı Analiz Raporunu Gör</a>
        <br><br>
        <a href="/sync" style="font-size: 16px; color: #3498db; text-decoration: none;">Verileri Şimdi Senkronize Et (/sync)</a>
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
            return "<h1>Henüz analiz edilecek veri bulunamadı. Lütfen önce /sync adresini ziyaret edin.</h1>"
            
        df = pd.DataFrame(data)
        
        # Analiz tabloları
        top_gol = df.sort_values(by="gls", ascending=False)[["squad", "gls", "mp", "sezon", "lig"]].head(10)
        top_pos = df.sort_values(by="possession", ascending=False)[["squad", "possession", "lig"]].head(10)
        
        df["verimlilik"] = df["gls"] / df["sh"].replace(0, 1)
        top_verim = df.sort_values(by="verimlilik", ascending=False)[["squad", "gls", "sh", "verimlilik", "lig"]].head(10)
        
        html_content = f"""
        <html>
            <head>
                <title>Futbol Analiz Raporu</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 30px; background: #f4f4f9; color: #333; }}
                    h1, h2 {{ color: #2c3e50; }}
                    table {{ width: 100%; border-collapse: collapse; margin-bottom: 40px; background: #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
                    th, td {{ padding: 12px 15px; border-bottom: 1px solid #ddd; text-align: left; }}
                    th {{ background-color: #2c3e50; color: white; }}
                    tr:hover {{ background-color: #f1f1f1; }}
                    .container {{ max-width: 1000px; margin: auto; }}
                    .btn {{ display: inline-block; padding: 10px 15px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <a href="/" class="btn">&larr; Ana Sayfaya Dön</a>
                    <h1>⚽ Futbol Analiz Paneli</h1>
                    <p>Supabase veritabanından çekilen güncel verilerle hazırlanan canlı rapor (Toplam <b>{len(df)}</b> takım incelendi).</p>
                    
                    <h2>🏆 En Çok Gol Atan İlk 10 Takım</h2>
                    {top_gol.to_html(index=False, classes='table', border=0)}
                    
                    <h2> possession Topa Sahip Olma Oranı En Yüksek İlk 10 Takım</h2>
                    {top_pos.to_html(index=False, classes='table', border=0)}
                    
                    <h2>🎯 Şut Verimliliği (Gol/Şut) En İyi Olan İlk 10 Takım</h2>
                    {top_verim.to_html(index=False, classes='table', border=0)}
                </div>
            </body>
        </html>
        """
        return html_content
    except Exception as e:
        return f"<h1>Analiz Hatası:</h1><p>{str(e)}</p>"

if __name__ == "__main__":
    app.run(debug=True)