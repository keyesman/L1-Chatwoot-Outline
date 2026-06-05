import requests
import sys
from datetime import datetime
from tabulate import tabulate

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL   = "https://chat.swiftoms.id"
API_TOKEN  = "TB7JiMR8y5NocemVXwQEqCKU"
ACCOUNT_ID = 2

HEADERS = {
    "api_access_token": API_TOKEN,
    "Content-Type": "application/json"
}


def seconds_to_human(seconds):
    if seconds is None:
        return "-"
    seconds = int(seconds)
    hours   = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs    = seconds % 60
    if hours > 0:
        return str(hours) + "h " + str(minutes) + "m " + str(secs) + "s"
    elif minutes > 0:
        return str(minutes) + "m " + str(secs) + "s"
    else:
        return str(secs) + "s"


def get_all_conversations(date_from=None, date_to=None):
    all_conversations = []
    page              = 1
    stop_pagination   = False

    print("[INFO] Mengambil data conversations...")

    while not stop_pagination:
        params = {
            "page": page,
            "status": "resolved"
        }
        response = requests.get(
            BASE_URL + "/api/v1/accounts/" + str(ACCOUNT_ID) + "/conversations",
            headers=HEADERS,
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            print("[GAGAL] Gagal ambil conversations. Status: " + str(response.status_code))
            break

        data          = response.json()
        conversations = data.get("data", {}).get("payload", [])

        if not conversations:
            break

        for conv in conversations:
            created_at = conv.get("created_at")
            if created_at:
                conv_date = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d")

                # Kalau sudah lebih tua dari date_from, tandai stop setelah page ini selesai
                if date_from and conv_date < date_from:
                    stop_pagination = True
                    continue

                # Skip kalau lebih baru dari date_to
                if date_to and conv_date > date_to:
                    continue

            all_conversations.append(conv)

        print("[INFO] Page " + str(page) + " -> ditemukan " + str(len(all_conversations)) + " conversations dalam range...")
        page += 1

    return all_conversations


def get_messages(conversation_id):
    response = requests.get(
        BASE_URL + "/api/v1/accounts/" + str(ACCOUNT_ID) + "/conversations/" + str(conversation_id) + "/messages",
        headers=HEADERS,
        timeout=10
    )
    if response.status_code != 200:
        return []
    return response.json().get("payload", [])


def get_last_note(messages):
    private_notes = [m for m in messages if m.get("private") is True]
    if not private_notes:
        return "-"
    content = private_notes[-1].get("content", "-")
    # Hapus newline agar tidak bikin gap di tabel
    content = content.replace("\n", " ").replace("\r", " ").strip()
    if content and len(content) > 50:
        content = content[:50] + "..."
    return content


def get_resolve_count(messages):
    # Hitung berapa kali status berubah jadi resolved dari activity messages
    count = 0
    for m in messages:
        content    = m.get("content", "") or ""
        msg_type   = m.get("message_type")
        # message_type 2 = activity
        if msg_type == 2 and "resolved" in content.lower():
            count += 1
    return count


def get_conversation_report(date_from=None, date_to=None):
    print("=" * 80)
    print("  CHATWOOT CONVERSATION REPORT")
    if date_from or date_to:
        print("  Periode: " + str(date_from or "-") + " s/d " + str(date_to or "-"))
    print("=" * 80)

    conversations = get_all_conversations(date_from, date_to)

    if not conversations:
        print("[INFO] Tidak ada data conversation ditemukan.")
        return

    print("[INFO] Total conversations: " + str(len(conversations)))
    print("[INFO] Mengambil detail tiap conversation...")
    print("")

    rows = []
    for conv in conversations:
        conv_id        = conv.get("id")
        created_at     = conv.get("created_at")
        assignee       = conv.get("meta", {}).get("assignee")
        agent_name     = assignee.get("name") if assignee else "-"
        labels         = conv.get("labels", [])
        labels_str     = ", ".join(labels) if labels else "-"
        created_dt     = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M") if created_at else "-"

        # Hitung FRT dari first_reply_created_at - created_at
        first_reply_at = conv.get("first_reply_created_at")
        frt            = (first_reply_at - created_at) if first_reply_at and created_at else None

        # Ambil messages — untuk last note & resolve count
        messages      = get_messages(conv_id)
        last_note     = get_last_note(messages)
        resolve_count = get_resolve_count(messages)
        is_reopened   = resolve_count > 1

        # Last resolution time: updated_at conversation (saat terakhir di-resolve)
        updated_at = conv.get("updated_at")
        last_rt    = (updated_at - created_at) if updated_at and created_at else None

        rows.append([
            "#" + str(conv_id),
            created_dt,
            agent_name,
            labels_str,
            seconds_to_human(frt),
            seconds_to_human(last_rt),
            str(resolve_count) + "x",
            "Yes" if is_reopened else "No",
            last_note
        ])

    headers = [
        "Ticket ID",
        "Created At",
        "Agent",
        "Labels",
        "First Resp Time",
        "Last Resol Time",
        "Resolve Count",
        "Reopened",
        "Last Note"
    ]

    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    print("")
    print("[DONE] Selesai. Total " + str(len(rows)) + " conversation ditampilkan.")


if __name__ == "__main__":
    get_conversation_report(
        date_from="2026-06-04",
        date_to="2026-06-05"
    )
