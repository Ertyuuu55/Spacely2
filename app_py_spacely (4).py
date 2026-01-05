import streamlit as st
import pandas as pd
import re

ICON_MAP = {
    "table": "🪵",
    "chair": "💺",
    "sofa": "🛋️",
    "desk": "🗄️",
    "bed": "🛏️"
}

# 1. Load DataFrame dari file CSV
github_csv_url = 'https://raw.githubusercontent.com/Ertyuuu55/Spacely2/main/Furniture%20(1).csv'
df = pd.read_csv(github_csv_url)


# 2. Parsing Function
def parse_user_prompt(prompt, df):
    prompt = prompt.lower()
    categories = df['category'].str.lower().unique()

    # Ambil semua angka beserta posisinya
    number_matches = [
        {
            "value": int(m.group().replace('.', '')),
            "start": m.start(),
            "end": m.end()
        }
        for m in re.finditer(r'\d{1,3}(?:\.\d{3})+|\d+', prompt)
    ]

    if not number_matches:
        return None, None, "Budget tidak ditemukan."

    # Budget = angka TERBESAR
    budget_item = max(number_matches, key=lambda x: x['value'])
    budget = budget_item['value']

    # Hapus budget dari kandidat quantity
    quantity_numbers = [
        n for n in number_matches if n != budget_item
    ]

    desired = []

    for cat in categories:
        for cat_match in re.finditer(rf'\b{cat}\b', prompt):
            cat_pos = cat_match.start()

            nearest = None
            min_distance = float('inf')

            for num in quantity_numbers:
                distance = min(
                    abs(num['start'] - cat_pos),
                    abs(num['end'] - cat_pos)
                )

                if distance < min_distance:
                    min_distance = distance
                    nearest = num

            if nearest:
                qty = nearest['value']
                quantity_numbers.remove(nearest)
            else:
                qty = 1

            desired.append({
                "category": cat,
                "quantity": qty
            })

    return budget, desired, None


# 3. Pemanggilan Output
def select_furniture_based_on_request(df, budget, requested_items):
    selected_items = []
    total_cost = 0
    messages = []

    # MODE 1: Tidak ada furniture spesifik
    if not requested_items:
        default_categories = ['table', 'sofa', 'chair', 'desk', 'bed']

        for cat in default_categories:
            cat_items = df[df['category'].str.lower() ==
                           cat].sort_values('price')
            if not cat_items.empty:
                item = cat_items.iloc[0]
                if total_cost + item['price'] <= budget:
                    selected_items.append(item.to_dict())
                    total_cost += item['price']

        if not selected_items:
            messages.append(
                "Budget tidak mencukupi untuk membeli furniture apa pun.")

        return selected_items, total_cost, messages

    # MODE 2: Ada furniture spesifik
    for req in requested_items:
        category = req['category']
        qty = req['quantity']

        cat_items = df[df['category'].str.lower() == category.lower()
                       ].sort_values('price')

        if cat_items.empty:
            messages.append(f"Tidak ada item untuk kategori {category}")
            continue

        selected_qty = 0

        for _, row in cat_items.iterrows():
            if selected_qty >= qty:
                break

            if total_cost + row['price'] <= budget:
                selected_items.append(row.to_dict())
                total_cost += row['price']
                selected_qty += 1
            else:
                break  # budget sudah tidak cukup, hentikan

        if selected_qty == 0:
            messages.append(
                f"Budget tidak mencukupi untuk kategori '{
                    category}' sebanyak {qty} item."
            )
        elif selected_qty < qty:
            messages.append(
                f"Budget hanya cukup untuk {selected_qty} dari {
                    qty} item kategori '{category}'."
            )
        else:
            messages.append(
                f"Berhasil memilih {qty} item untuk kategori '{category}'."
            )

    return selected_items, total_cost, messages


# 4. Streamlit Application UI
st.set_page_config(layout="centered", page_title="Furniture Recommender")
st.title("Furniture Recommendation System")
st.write("Masukkan budget Anda (dalam Rupiah) dan kategori furniture yang diinginkan beserta jumlahnya untuk mendapatkan rekomendasi.")

st.header("Chat Input")

user_prompt = st.text_input(
    "Masukkan kebutuhan furniture Anda (budget WAJIB)",
    placeholder="Contoh: Budget Rp 5000000, bed 2, chair (min 811.268)"
)


# Fungsi supaya angka menggunakan format rupiah yang mudah dibaca,
# misal 100000 menjadi Rp100.000
def format_rupiah(angka):
    return f"Rp{int(angka):,}".replace(",", ".")


# Button untuk menampilkan rekomendasi
if st.button("Generate Recommendations"):
    if not user_prompt.strip():
        st.error(
            "Input tidak boleh kosong atau budget tidak ditemukan. Pastikan Anda menyertakan 'Budget [jumlah]' atau 'Rp [jumlah]'.")
    else:
        user_budget, user_desired_categories, error = parse_user_prompt(
            user_prompt, df)

        if error:
            st.error(error)
        else:
            USD_TO_IDR = 16000
            user_budget_idr = user_budget
            user_budget_usd = user_budget_idr / USD_TO_IDR
            st.markdown("""
            <style>
            .furniture-card {
                padding: 18px;
                border-radius: 14px;
                margin-bottom: 16px;
                box-shadow: 3px 3px 20px rgba(0,0,0);
            }
            .furniture-title {
                font-size: 22px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            .furniture-item {
                font-size: 15px;
                margin: 4px 0;
            }
            </style>
            """, unsafe_allow_html=True)

            st.subheader("Recommendation Results")

            results, total_cost_usd, messages = select_furniture_based_on_request(
                df, user_budget_usd, user_desired_categories
            )

            total_cost_idr = total_cost_usd * USD_TO_IDR
            remaining_budget_idr = user_budget_idr - total_cost_idr

            for msg in messages:
                st.info(msg)

            if results:
                result_df = pd.DataFrame(results)

                for item in results:
                    icon = ICON_MAP.get(item['category'].lower(), "🛒")

                    st.markdown(f"""
                    <div class="furniture-card">
                        <div class="furniture-title">{icon} {item['category'].capitalize()}</div>
                        <div class="furniture-item"><b>Harga:</b> {format_rupiah(item['price'] * USD_TO_IDR)}</div>
                        <div class="furniture-item"><b>Material:</b> {item['material']}</div>
                        <div class="furniture-item"><b>Warna:</b> {item['color']}</div>
                    </div>
                    """.replace(",", "."), unsafe_allow_html=True)

                st.success(f"Total Biaya: {format_rupiah(total_cost_idr)}")

                if remaining_budget_idr > 0:
                    st.info(f"Sisa Budget Anda: {
                            format_rupiah(remaining_budget_idr)}")
                    # Suggestion tambahan (tidak otomatis)
                    suggestions = df[
                        (df['price'] * USD_TO_IDR <= remaining_budget_idr)
                    ].sort_values('price').head(3)

                    if not suggestions.empty:
                        st.markdown(
                            "💡 *Dengan sisa budget ini, Anda masih bisa membeli:*")
                        for _, row in suggestions.iterrows():
                            icon = ICON_MAP.get(row['category'].lower(), "🛒")
                            st.write(
                                f"- {icon} {row['category'].capitalize()} — {format_rupiah(row['price'] * USD_TO_IDR)}")

                elif remaining_budget_idr == 0:
                    st.info("Budget Anda pas.")
                else:
                    st.warning("Budget tidak mencukupi")
            else:
                st.warning("Tidak ada furniture yang bisa direkomendasikan.")
