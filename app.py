from flask import Flask, jsonify
import os
from islemci import verileri_isle_ve_yukle

app = Flask(__name__)

@app.route("/")
def index():
    return "Futbol Analiz V2 Sistemi Aktif, Supabase Senkronizasyonu Hazır!"

@app.route("/sync", methods=["GET", "POST"])
def sync():
    """Tarayıcıdan veya dış servisten bu adrese istek atıldığında verileri günceller."""
    basarili = verileri_isle_ve_yukle()
    if basarili:
        return jsonify({"durum": "başarılı", "mesaj": "Veriler başarıyla işlendi ve Supabase'e aktarıldı."}), 200
    else:
        return jsonify({"durum": "hata", "mesaj": "Aktarım sırasında bir hata oluştu. Logları kontrol edin."}), 500

# Render servisi (gunicorn app:app) ayağa kalktığında otomatik senkronizasyon tetiklemesi
try:
    print("Render servisi başlatılıyor, otomatik senkronizasyon deneniyor...")
    verileri_isle_ve_yukle()
except Exception as e:
    print(f"Otomatik başlatma sırasında hata: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)