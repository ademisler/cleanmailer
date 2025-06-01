
import pandas as pd
import os

# Dosya yolları
ACTIVE_MAILS = "/opt/mail_oto/reports/aktif_mailler.xlsx"
BOUNCED = "/opt/mail_oto/reports/bounced.xlsx"
REPLIED = "/opt/mail_oto/reports/replied.xlsx"
OUTPUT_FILE = "/opt/mail_oto/reports/temiz_liste_final.xlsx"

# Aktif mailleri yükle
df_active = pd.read_excel(ACTIVE_MAILS)

# Hatalı (bounced) adresler
bounced_emails = []
if os.path.exists(BOUNCED):
    df_bounced = pd.read_excel(BOUNCED)
    bounced_emails = df_bounced["email"].str.lower().unique().tolist()

# Yanıtlanan (replied) adresler
replied_emails = []
if os.path.exists(REPLIED):
    df_replied = pd.read_excel(REPLIED)
    replied_emails = df_replied["email"].str.lower().unique().tolist()

# Temiz listeyi oluştur
df_active["email"] = df_active["email"].str.lower()
df_clean = df_active[~df_active["email"].isin(bounced_emails)]

# Geri dönüş almışlar etiketlensin
df_clean["replied"] = df_clean["email"].isin(replied_emails)

# Excel olarak kaydet
df_clean.to_excel(OUTPUT_FILE, index=False)

print(f"Temiz liste oluşturuldu: {len(df_clean)} adres kaydedildi.")


# Temiz listeyi /checked/ klasörüne yedekle
import shutil
from datetime import datetime

backup_path = f"/opt/mail_oto/checked/temiz_liste_{datetime.now().strftime('%Y%m%d')}.xlsx"
shutil.copy(OUTPUT_FILE, backup_path)

print(f"Yedek kopya oluşturuldu: {backup_path}")
