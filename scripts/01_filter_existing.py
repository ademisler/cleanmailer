
import pandas as pd
import os

# Proje kök dizini ortam değişkeninden okunur, yoksa varsayılanı kullanılır
ROOT = os.environ.get("MAIL_OTO_HOME", "/opt/mail_oto")

INPUT_PATH = os.path.join(ROOT, "input", "Receivers.xlsx")
CHECKED_DIR = os.path.join(ROOT, "checked")
REPORT_PATH = os.path.join(ROOT, "reports", "kontrol_edilmemis.xlsx")

# Alıcı listesini oku
df_receivers = pd.read_excel(INPUT_PATH)

# checked klasöründeki daha önce gönderilmiş adresleri topla
checked_emails = set()
for fname in os.listdir(CHECKED_DIR):
    if fname.endswith(".xlsx"):
        df_checked = pd.read_excel(os.path.join(CHECKED_DIR, fname))
        checked_emails.update(df_checked['email'].dropna().str.lower().tolist())

# Eğer email kolonu varsa, filtrele
if 'email' in df_receivers.columns:
    df_receivers['email'] = df_receivers['email'].str.lower()
    df_new = df_receivers[~df_receivers['email'].isin(checked_emails)]
else:
    raise ValueError("Excel dosyasında 'email' sütunu bulunamadı.")

# Sonuçları kaydet
df_new.to_excel(REPORT_PATH, index=False)
print(f"{len(df_new)} yeni e-posta adresi bulundu ve kaydedildi: {REPORT_PATH}")
