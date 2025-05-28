from flask import Flask, request, redirect, url_for, session, render_template_string, send_from_directory
import os
from werkzeug.utils import secure_filename
import urllib.parse  # vCard linki için encode

app = Flask(__name__)
app.secret_key = 'yurtyapi25885'  # Güvenlik için değiştirin
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 600 * 1024 * 1024  # 600MB limit (changed from 16MB)

# Otomatik upload klasörü oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Şirket bilgileri
company_info = {
    "name": "YURT YAPI ALEMİNYUM SİSTEMLERİ",
    "phone": "+905353133790",
    "email": "info@yurtyapialeminyum.com",
    "founder": "İSMAİL YEŞİLYURT",
    "website": "https://yurtyapialuminyum.com/",
    "address": "İnönü mahallesi 361 sk no 48 BAĞCILAR / İSTANBUL"
}

# Mobil uyumlu HTML şablonları (SADECE GİRİŞ ŞABLONUNDAN ŞİFRE KISMI KALDIRILDI)
MOBILE_LOGIN = '''
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Yurt Yapı Giriş</title>
    <style>
        * {box-sizing: border-box;}
        body {font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f0f2f5;}
        .container {padding: 20px; height: 100vh; display: flex; flex-direction: column; justify-content: center;}
        .login-card {background: white; border-radius: 10px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
        h2 {text-align: center; color: #333; margin-bottom: 20px;}
        button {width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 5px; font-size: 16px;}
    </style>
</head>
<body>
    <div class="container">
        <div class="login-card">
            <h2>YURT YAPI</h2>
            <form method="POST">
                <button type="submit">GİRİŞ YAP</button>
            </form>
        </div>
    </div>
</body>
</html>
'''

MOBILE_DASHBOARD = '''
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ company.name }}</title>
    <style>
        * {box-sizing: border-box;}
        body {font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f0f2f5;}
        .header {background: #3498db; color: white; padding: 15px; text-align: center;}
        .logout-btn {position: absolute; right: 10px; top: 15px; background: #e74c3c; color: white; border: none; padding: 5px 10px; border-radius: 3px;}
        .card {background: white; margin: 15px; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
        .info-item {margin-bottom: 10px;}
        .vcard-btn {display: block; text-align: center; background: #2ecc71; color: white; padding: 10px; border-radius: 5px; text-decoration: none; margin-top: 15px;}
        .upload-form {margin-top: 20px;}
        .file-list {margin-top: 15px;}
        .file-item {padding: 12px 0; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;}
        .file-actions {display: flex; gap: 8px;}
        .btn {padding: 8px 12px; border-radius: 4px; text-decoration: none; font-size: 14px;}
        .download-btn {background: #3498db; color: white;}
        .delete-btn {background: #e74c3c; color: white; border: none; cursor: pointer;}
        .no-files {text-align: center; color: #777; padding: 15px;}
    </style>
</head>
<body>
    <div class="header">
        <h2>{{ company.name }}</h2>
        <form action="/logout" method="POST" style="display:inline;">
            <button type="submit" class="logout-btn">Çıkış</button>
        </form>
    </div>
    
    <div class="card">
        <h3>İletişim Bilgileri</h3>
        <div class="info-item"><strong>Tel:</strong> <a href="tel:{{ company.phone }}">{{ company.phone }}</a></div>
        <div class="info-item"><strong>E-posta:</strong> <a href="mailto:{{ company.email }}">{{ company.email }}</a></div>
        <div class="info-item"><strong>Adres:</strong> {{ company.address }}</div>
        
        <a href="{{ vcard_link }}" download="yurt_yapi.vcf" class="vcard-btn">
            Rehbere Kaydet
        </a>
    </div>
    
    <div class="card">
        <h3>Dosya Yöneticisi</h3>
        <form class="upload-form" method="POST" enctype="multipart/form-data" action="/upload">
            <input type="file" name="file" style="width:100%; margin-bottom:10px;" required>
            <button type="submit" class="btn download-btn" style="width:100%;">Dosya Yükle</button>
        </form>
        
        <div class="file-list">
            {% for file in files %}
            <div class="file-item">
                <span>{{ file }}</span>
                <div class="file-actions">
                    <a href="/download/{{ file }}" class="btn download-btn">İndir</a>
                    <form action="/delete/{{ file }}" method="POST" style="display:inline;">
                        <button type="submit" class="btn delete-btn" onclick="return confirm('Dosyayı silmek istediğinize emin misiniz?');">Sil</button>
                    </form>
                </div>
            </div>
            {% else %}
            <div class="no-files">Henüz dosya yok</div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def mobile_login():
    if request.method == 'POST':
        session['authenticated'] = True
        return redirect(url_for('mobile_dashboard'))
    return render_template_string(MOBILE_LOGIN)

@app.route('/dashboard')
def mobile_dashboard():
    if not session.get('authenticated'):
        return redirect(url_for('mobile_login'))
    
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    
    # vCard içeriğini url encode ile güvenli yapalım
    vcard = (
        "BEGIN:VCARD\nVERSION:3.0\n"
        f"N:{company_info['name']}\n"
        f"TEL:{company_info['phone']}\n"
        f"EMAIL:{company_info['email']}\n"
        f"URL:{company_info['website']}\n"
        f"ADR:{company_info['address']}\n"
        f"NOTE:Kurucu: {company_info['founder']}\n"
        "END:VCARD"
    )
    vcard_encoded = "data:text/vcard;charset=utf-8," + urllib.parse.quote(vcard)
    
    return render_template_string(
        MOBILE_DASHBOARD,
        company=company_info,
        files=files,
        vcard_link=vcard_encoded
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    if not session.get('authenticated'):
        return redirect(url_for('mobile_login'))
    
    if 'file' not in request.files:
        return redirect(url_for('mobile_dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('mobile_dashboard'))
    
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    return redirect(url_for('mobile_dashboard'))

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if not session.get('authenticated'):
        return redirect(url_for('mobile_login'))
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    return redirect(url_for('mobile_dashboard'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('mobile_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
