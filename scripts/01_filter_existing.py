
import pandas as pd
import os

INPUT_PATH = "/opt/mail_oto/input/Receivers.xlsx"
CHECKED_DIR = "/opt/mail_oto/checked/"
REPORT_PATH = "/opt/mail_oto/reports/kontrol_edilmemis.xlsx"

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
