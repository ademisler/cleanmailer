
import os
import pandas as pd


ROOT = os.environ.get("CLEANMAILER_HOME", "/opt/cleanmailer")
INPUT_PATH = os.path.join(ROOT, "input", "Receivers.xlsx")
CHECKED_DIR = os.path.join(ROOT, "checked")
REPORT_PATH = os.path.join(ROOT, "reports", "kontrol_edilmemis.xlsx")


def filter_existing():
    """Filter out emails that were already contacted."""
    df_receivers = pd.read_excel(INPUT_PATH)

    os.makedirs(CHECKED_DIR, exist_ok=True)
    checked_emails = set()
    for fname in os.listdir(CHECKED_DIR):
        if fname.endswith(".xlsx"):
            df_checked = pd.read_excel(os.path.join(CHECKED_DIR, fname))
            if "email" in df_checked.columns:
                checked_emails.update(
                    df_checked["email"].dropna().str.lower().tolist()
                )

    if "email" not in df_receivers.columns:
        raise ValueError("Excel dosyasında 'email' sütunu bulunamadı.")

    df_receivers["email"] = df_receivers["email"].str.lower()
    df_new = df_receivers[~df_receivers["email"].isin(checked_emails)]

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    df_new.to_excel(REPORT_PATH, index=False)
    print(
        f"{len(df_new)} yeni e-posta adresi bulundu ve kaydedildi: {REPORT_PATH}"
    )


if __name__ == "__main__":
    filter_existing()
