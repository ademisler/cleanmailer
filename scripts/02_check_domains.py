
import pandas as pd
import dns.resolver

INPUT_FILE = "/opt/mail_oto/reports/kontrol_edilmemis.xlsx"
ACTIVE_OUTPUT = "/opt/mail_oto/reports/aktif_mailler.xlsx"
INACTIVE_OUTPUT = "/opt/mail_oto/reports/inactive_domains.xlsx"

# Dosyayı oku
df = pd.read_excel(INPUT_FILE)

# Domain çıkar
df['domain'] = df['email'].str.extract(r'@(.+)$')

# Aktiflik kontrol fonksiyonu
def is_domain_active(domain):
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except:
        try:
            dns.resolver.resolve(domain, 'A')
            return True
        except:
            return False

# Domain kontrolü
df['is_active'] = df['domain'].apply(is_domain_active)

# Aktif ve inaktif ayrımı
df_active = df[df['is_active'] == True].drop(columns=['is_active'])
df_inactive = df[df['is_active'] == False].drop(columns=['is_active'])

# Kayıt
df_active.to_excel(ACTIVE_OUTPUT, index=False)
df_inactive.to_excel(INACTIVE_OUTPUT, index=False)

print(f"Aktif: {len(df_active)} mail | Pasif: {len(df_inactive)} mail")
