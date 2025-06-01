
import os
import pandas as pd
import dns.resolver
from dns.exception import DNSException

ROOT = os.environ.get("MAIL_OTO_HOME", "/opt/mail_oto")
INPUT_FILE = os.path.join(ROOT, "reports", "kontrol_edilmemis.xlsx")
ACTIVE_OUTPUT = os.path.join(ROOT, "reports", "aktif_mailler.xlsx")
INACTIVE_OUTPUT = os.path.join(ROOT, "reports", "inactive_domains.xlsx")

def is_domain_active(domain):
    try:
        dns.resolver.resolve(domain, "MX")
        return True
    except DNSException:
        try:
            dns.resolver.resolve(domain, "A")
            return True
        except DNSException as exc:
            print(f"[WARN] {domain} kontrol edilemedi: {exc}")
            return False


def main():
    os.makedirs(os.path.dirname(ACTIVE_OUTPUT), exist_ok=True)
    df = pd.read_excel(INPUT_FILE)

    if "email" not in df.columns:
        raise ValueError("Excel dosyasında 'email' sütunu bulunamadı.")

    df['domain'] = df['email'].str.extract(r'@(.+)$')

    df['is_active'] = df['domain'].apply(is_domain_active)

    df_active = df[df['is_active'] == True].drop(columns=['is_active'])
    df_inactive = df[df['is_active'] == False].drop(columns=['is_active'])

    df_active.to_excel(ACTIVE_OUTPUT, index=False)
    df_inactive.to_excel(INACTIVE_OUTPUT, index=False)

    print(f"Aktif: {len(df_active)} mail | Pasif: {len(df_inactive)} mail")


if __name__ == "__main__":
    main()
